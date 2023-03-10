import time

from predictors.tasks.prediction_tasks import predict_icons_task

if __name__ == "__main__":
    start_time = time.time()
    for _ in range(10):
        predict_icons_task(image_name="profiling-test-image.png")
    print(f"Total time: {time.time() - start_time} seconds")
