import glob
import shutil
from os import path
from pathlib import Path

# First we copy the labels
labels_source_folder = "data/yolo_labels"
images_source_folder = "data/swiss-dwellings/images"
destination_folder = "darknet_yolo/data/obj"

Path(destination_folder).mkdir(parents=True, exist_ok=True)

for filename in glob.iglob(path.join(labels_source_folder, "*.txt")):
    # copy label
    shutil.copy(filename, destination_folder)
    # Copy image
    title, ext = path.splitext(path.basename(filename))
    shutil.copy(path.join(images_source_folder, f"{title}.jpg"), destination_folder)


# Create the train.txt and test.txt files
percentage_test = 10  # Percentage of images to be used for the test set

file_train = Path("darknet_yolo/data/train.txt")
file_test = Path("darknet_yolo/data/test.txt")

index_test = round(100 / percentage_test)
with file_train.open("w") as f_train, file_test.open("w") as f_test:
    for i, filename in enumerate(glob.iglob(path.join(destination_folder, "*.jpg"))):
        title, ext = path.splitext(path.basename(filename))

        if i % index_test == 0:
            f_test.write(f"data/obj/{title}.jpg\n")
        else:
            f_train.write(f"data/obj/{title}.jpg\n")
