from itertools import product

import numpy as np
from detectron2.evaluation import COCOEvaluator


class COCOEvaluatorDetailed(COCOEvaluator):
    """
    This class adds AR as well as AP50 and AP75 on class level
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
