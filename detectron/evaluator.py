from itertools import product

import cv2
import numpy as np
from detectron2.evaluation import COCOEvaluator
from detectron2.evaluation.coco_evaluation import instances_to_coco_json
from detectron2.structures import BoxMode
from shapely.geometry import box


class COCOEvaluatorDetailed(COCOEvaluator):
    """
    This class adds Precision, AR as well as AP50 and AP75 on class level
    """

    def _derive_coco_results(self, coco_eval, iou_type, class_names=None):
        stats = super()._derive_coco_results(coco_eval, iou_type, class_names)

        iou_indexes = [0, 5, slice(None, None)]
        iou_labels = ["50", "75", ""]
        ar_labels = ["AR", "ARs", "ARm", "ARl"]

        if not coco_eval:
            stats.update(zip(ar_labels, len(ar_labels) * [float("nan")]))
            stats.update(
                (f"AP{iou_label}-{cls_name}", float("nan"))
                for cls_name, iou_label in product(class_names, iou_labels[:2])
            )
            stats.update(
                (f"AR{iou_label}-{cls_name}", float("nan"))
                for cls_name, iou_label in product(class_names, iou_labels)
            )
        else:
            stats.update(
                zip(
                    ar_labels,
                    map(
                        lambda s: float("nan") if s == -1 else float(s * 100),
                        coco_eval.stats[8:],
                    ),
                )
            )
            # class level evaluations
            recalls = coco_eval.eval["recall"]
            for (idx, cls_name), (iou_label, iou_index) in product(
                enumerate(class_names), zip(iou_labels, iou_indexes)
            ):
                recall_cls = recalls[iou_index, idx, 0, -1]
                recall_cls = recall_cls[recall_cls > -1]
                ar = np.mean(recall_cls) if recall_cls.size else float("nan")
                stats[f"AR{iou_label}-{cls_name}"] = float(ar * 100)

            precisions = coco_eval.eval["precision"]
            for (idx, cls_name), (iou_label, iou_index) in product(
                enumerate(class_names), zip(iou_labels[:2], iou_indexes)
            ):
                precision_cls = precisions[iou_index, :, idx, 0, -1]
                precision_cls = precision_cls[precision_cls > -1]
                ap = np.mean(precision_cls) if precision_cls.size else float("nan")
                stats[f"AP{iou_label}-{cls_name}"] = float(ap * 100)

        return stats


class BBoxEvaluator:
    def __init__(self, predictor, dataset_dicts, thing_classes, min_score):
        self.predictor = predictor
        self.min_score = min_score
        self.dataset_dicts = dataset_dicts
        self.thing_classes = thing_classes
        self.iou_level = 50  # list(range(50, 100, 5))

    @staticmethod
    def to_shapely_box(bbox, bbox_mode):
        return box(
            *BoxMode.convert(box=bbox, from_mode=bbox_mode, to_mode=BoxMode.XYXY_ABS)
        )

    @staticmethod
    def compute_iou(bbox_gt, bbox_pr):
        return bbox_pr.intersection(bbox_gt).area / bbox_pr.union(bbox_gt).area

    @classmethod
    def find_prediction(cls, annotation, predictions, iou_level):
        # print(annotation["bbox"], predictions[0]["bbox"])
        bbox_gt = cls.to_shapely_box(
            bbox=annotation["bbox"], bbox_mode=annotation["bbox_mode"]
        )
        pred_bboxes = [
            cls.to_shapely_box(bbox=pred["bbox"], bbox_mode=BoxMode.XYWH_ABS)
            for pred in predictions
        ]
        iou = [cls.compute_iou(bbox_gt, bbox_pr) for bbox_pr in pred_bboxes]
        best_pred, best_iou = max(
            zip(predictions, iou),
            key=lambda pred_iou: (pred_iou[1], pred_iou[0]["score"]),
            default=(None, 0.0),
        )
        if best_iou >= iou_level:
            return best_pred

    @classmethod
    def recall_and_precision(cls, annotations, predictions, iou_level):
        predictions = list(predictions)
        false_neg = 0
        false_pos = 0
        true_pos = 0

        if not predictions:
            false_neg += len(annotations)
            score = float("nan")
            precision = float("nan")
            recall = float(0 if annotations else "nan")
        elif not annotations:
            false_pos = len(predictions)
            score = sum(p["score"] for p in predictions) / len(predictions)
            precision = float(0 if predictions else "nan")
            recall = float("nan")
        else:
            score = sum(p["score"] for p in predictions) / len(predictions)
            for annotation in annotations:
                if prediction := cls.find_prediction(
                    annotation, predictions, iou_level
                ):
                    predictions.remove(prediction)
                    true_pos += 1
                else:
                    false_neg += 1

            false_pos = len(predictions)
            precision = true_pos / (true_pos + false_pos)
            recall = true_pos / (true_pos + false_neg)

        return {
            "false_neg": false_neg,
            "false_pos": false_pos,
            "true_pos": true_pos,
            "precision": precision,
            "recall": recall,
            "score": score,
        }

    def get_predictions_coco_json(self, dataset_dict):
        return list(
            instances_to_coco_json(
                self.predictor(cv2.imread(dataset_dict["file_name"]))["instances"].to(
                    "cpu"
                ),
                dataset_dict["image_id"],
            )
        )

    def get_evaluations(self, dataset_dict, predictions):
        return {
            class_name: self.recall_and_precision(
                annotations=list(
                    filter(
                        lambda a_gt: a_gt["category_id"] == category_id,
                        dataset_dict["annotations"],
                    )
                ),
                predictions=list(
                    filter(
                        lambda r: r["category_id"] == category_id
                        and r["score"] >= self.min_score,
                        predictions,
                    )
                ),
                iou_level=self.iou_level / 100,
            )
            for category_id, class_name in enumerate(self.thing_classes)
        }

    def aggregate_evaluations(self, evaluations_by_image):
        precision_and_recall = {}
        for thing_class in self.thing_classes:
            false_pos, false_neg, true_pos = [
                sum(
                    evaluations[thing_class][field]
                    for evaluations in evaluations_by_image.values()
                )
                for field in ["false_pos", "false_neg", "true_pos"]
            ]
            precision_and_recall[thing_class] = dict(
                false_pos=false_pos,
                false_neg=false_neg,
                true_pos=true_pos,
                precision=(
                    (true_pos / (true_pos + false_pos))
                    if (true_pos + false_pos)
                    else float("nan")
                ),
                recall=(
                    (true_pos / (true_pos + false_neg))
                    if (true_pos + false_neg)
                    else float("nan")
                ),
            )
        return precision_and_recall

    def evaluate(self):
        evaluations_by_image = {}
        predictions_by_image = {}
        for dataset_dict in self.dataset_dicts:
            predictions = self.get_predictions_coco_json(dataset_dict)
            evaluations_by_image[dataset_dict["file_name"]] = self.get_evaluations(
                dataset_dict, predictions
            )
            predictions_by_image[dataset_dict["file_name"]] = predictions

        dataset_evaluations = self.aggregate_evaluations(
            evaluations_by_image=evaluations_by_image
        )
        return dataset_evaluations, predictions_by_image, evaluations_by_image
