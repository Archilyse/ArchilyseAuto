from pathlib import Path

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pytorch_lightning as pl
import segmentation_models_pytorch as smp
import torch
from dataset import COCOSegementationDataset


def get_preprocessing_fn(encoder: str, encoder_weights: str):
    return smp.encoders.get_preprocessing_fn(encoder, encoder_weights)


class FloorplanModel(pl.LightningModule):
    def __init__(
        self,
        class_names,
        learning_rate,
        loss_function,
        encoder,
        encoder_weights,
        activation,
        output_directory,
        validation_dataset,
        mlflow_tracking_uri,
        mlflow_experiment_name,
        mlflow_run_name,
        tversky_params,
        config,
        mean,
        std,
        **kwargs,
    ):
        super().__init__()
        output_directory.mkdir(parents=True, exist_ok=True)

        self.model = smp.DeepLabV3Plus(
            encoder_name=encoder,
            encoder_weights=encoder_weights,
            classes=len(class_names),
            activation=activation,
        )

        self.class_names = class_names
        self.learning_rate = learning_rate
        self.activation = activation
        self.encoder = encoder
        self.encoder_weights = encoder_weights
        self.output_directory = output_directory
        self.validation_dataset = validation_dataset
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.mlflow_experiment_name = mlflow_experiment_name
        self.mlflow_run_name = mlflow_run_name
        self.mlflow_initialized = False

        if mean is not None and std is not None:
            self.register_buffer("std", torch.tensor(mean).view(1, 3, 1, 1))
            self.register_buffer("mean", torch.tensor(std).view(1, 3, 1, 1))
        else:
            params = smp.encoders.get_preprocessing_params(encoder)
            self.register_buffer("std", torch.tensor(params["std"]).view(1, 3, 1, 1))
            self.register_buffer("mean", torch.tensor(params["mean"]).view(1, 3, 1, 1))

        self.config = config

        # loss function
        if loss_function == "tversky":
            alpha, beta, gamma = tversky_params
            self.loss_fn = smp.losses.TverskyLoss(
                smp.losses.MULTILABEL_MODE,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
                from_logits=activation is None,
            )
        elif loss_function == "dice":
            self.loss_fn = smp.losses.DiceLoss(
                smp.losses.MULTILABEL_MODE,
                from_logits=activation is None,
            )
        elif loss_function == "cross_entropy":
            self.loss_fn = smp.losses.SoftCrossEntropyLoss(smp.losses.MULTILABEL_MODE)
        elif loss_function == "miou":
            self.loss_fn = smp.losses.JaccardLoss(
                smp.losses.MULTILABEL_MODE, from_logits=activation is None
            )
        else:
            raise ValueError("Unknown loss function")

    def forward(self, image):
        # image = (image - self.mean) / self.std
        mask = self.model(image)
        return mask

    def shared_step(self, batch, stage):
        image, mask = batch
        assert image.ndim == 4
        h, w = image.shape[2:]
        assert h % 32 == 0 and w % 32 == 0
        assert mask.ndim == 4
        assert mask.max() <= 1.0 and mask.min() >= 0

        logits_mask = self.forward(image)
        loss = self.loss_fn(logits_mask, mask)

        if self.activation is None:
            prob_mask = torch.nn.Softmax2d(logits_mask)
        else:
            prob_mask = logits_mask

        pred_mask = (prob_mask > 0.5).float()
        tp, fp, fn, tn = smp.metrics.get_stats(
            pred_mask.long(), mask.long(), mode="multilabel"
        )
        results = {
            "loss": loss,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }

        for i, class_name in enumerate(self.class_names):
            tp, fp, fn, tn = smp.metrics.get_stats(
                pred_mask[:, i].long(), mask[:, i].long(), mode="binary"
            )
            results = {
                **results,
                f"tp-{class_name}": tp,
                f"fp-{class_name}": fp,
                f"fn-{class_name}": fn,
                f"tn-{class_name}": tn,
            }

        return results

    def shared_epoch_end(self, outputs, stage):
        # aggregate step metics
        loss = np.array([x["loss"].cpu().numpy() for x in outputs])
        tp = torch.cat([x["tp"] for x in outputs])
        fp = torch.cat([x["fp"] for x in outputs])
        fn = torch.cat([x["fn"] for x in outputs])
        tn = torch.cat([x["tn"] for x in outputs])

        # per image IoU means that we first calculate IoU score for each image
        # and then compute mean over these scores
        per_image_iou = smp.metrics.iou_score(
            tp, fp, fn, tn, reduction="micro-imagewise"
        )

        # dataset IoU means that we aggregate intersection and union over whole dataset
        # and then compute IoU score. The difference between dataset_iou and per_image_iou scores
        # in this particular case will not be much, however for dataset
        # with "empty" images (images without target class) a large gap could be observed.
        # Empty images influence a lot on per_image_iou and much less on dataset_iou.
        dataset_iou = smp.metrics.iou_score(tp, fp, fn, tn, reduction="micro")

        metrics = {
            f"{stage}_loss": loss.mean(),
            f"{stage}_per_image_iou": per_image_iou,
            f"{stage}_dataset_iou": dataset_iou,
        }
        for class_name in self.class_names:
            tp = torch.cat([x[f"tp-{class_name}"] for x in outputs])
            fp = torch.cat([x[f"fp-{class_name}"] for x in outputs])
            fn = torch.cat([x[f"fn-{class_name}"] for x in outputs])
            tn = torch.cat([x[f"tn-{class_name}"] for x in outputs])

            per_image_iou = smp.metrics.iou_score(
                tp, fp, fn, tn, reduction="micro-imagewise"
            )
            dataset_iou = smp.metrics.iou_score(tp, fp, fn, tn, reduction="micro")

            metrics = {
                **metrics,
                f"{stage}_{class_name}_per_image_iou": per_image_iou,
                f"{stage}_{class_name}_dataset_iou": dataset_iou,
            }

        self.log_dict(metrics, prog_bar=True)

        if self.global_rank == 0 and not self.trainer.sanity_checking:
            if not self.mlflow_initialized:
                mlflow.set_tracking_uri(uri=self.mlflow_tracking_uri)
                mlflow.set_experiment(experiment_name=self.mlflow_experiment_name)
                mlflow.start_run(run_name=self.mlflow_run_name)
                self.mlflow_initialized = True

                for k, v in self.config.items():
                    mlflow.log_param(k, v)

            for k, v in metrics.items():
                mlflow.log_metric(key=k, value=v, step=self.current_epoch)

            if stage == "valid" and self.current_epoch % 3 == 0:
                plots_path = self.output_directory.joinpath(
                    f"plots/{self.current_epoch}"
                )
                self.generate_plots(
                    model=self.model,
                    dataset=self.validation_dataset,
                    output_directory=plots_path,
                )
                mlflow.log_artifacts(plots_path.as_posix(), plots_path.name)

                model_path = self.output_directory.joinpath("model.pth").as_posix()
                torch.save(self.model, model_path)
                mlflow.log_artifact(model_path, "model")

    def training_step(self, batch, batch_idx):
        return self.shared_step(batch, "train")

    def training_epoch_end(self, outputs):
        return self.shared_epoch_end(outputs, "train")

    def validation_step(self, batch, batch_idx):
        return self.shared_step(batch, "valid")

    def validation_epoch_end(self, outputs):
        return self.shared_epoch_end(outputs, "valid")

    def test_step(self, batch, batch_idx):
        return self.shared_step(batch, "test")

    def test_epoch_end(self, outputs):
        return self.shared_epoch_end(outputs, "test")

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.learning_rate)

    def generate_plots(
        self,
        model,
        dataset: COCOSegementationDataset,
        output_directory: Path,
        num_samples: int = 10,
        conf_threshold: float = 0.1,
    ):
        with torch.no_grad():
            model.eval()

            output_directory.mkdir(exist_ok=True, parents=True)
            for i in range(num_samples):
                image, gt_mask = dataset[i]
                x_tensor = torch.from_numpy(image).to("cpu").unsqueeze(0)
                # x_tensor_normalized = (x_tensor - self.mean.to("cpu")) / self.std.to(
                #     "cpu"
                # )
                pred_mask = model(x_tensor.to("cuda")).detach().squeeze().cpu().numpy()
                start_dim = 1 if dataset.add_background_dim else 0

                fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4, figsize=(40, 10))
                ax1.imshow(image.transpose(1, 2, 0))
                ax2.imshow(
                    dataset.get_mask_rgb(
                        dataset.get_mask_flat(gt_mask[start_dim:].transpose(1, 2, 0))
                    )
                )
                ax3.imshow(
                    dataset.get_mask_rgb(
                        np.argmax(pred_mask.transpose(1, 2, 0), axis=-1).reshape(
                            pred_mask.shape[1], pred_mask.shape[2], 1
                        ),
                        values=list(
                            range(start_dim, len(dataset.category_ids) + start_dim)
                        ),
                    )
                )
                ax4.imshow(
                    dataset.get_mask_rgb(
                        dataset.get_mask_flat(
                            pred_mask[start_dim:].transpose(1, 2, 0) >= conf_threshold
                        )
                    )
                )

                output_path = output_directory.joinpath(f"{i}.png")
                plt.savefig(
                    output_path.as_posix(), bbox_inches="tight", dpi=150, pad_inches=0
                )
                fig.clear()
                plt.close()
                plt.cla()
                plt.clf()
