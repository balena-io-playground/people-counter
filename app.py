"""
Sample application using object detection and centroid tracking to 
determine the number of non-unique people who pass in view, as well
display general metrics on total number of people, average time seen,
and longest time detected.
"""

import time
import edgeiq
import metrics_manager


def main():
    obj_detect = edgeiq.ObjectDetection("alwaysai/mobilenet_ssd")
    obj_detect.load(engine=edgeiq.Engine.DNN_OPENVINO)

    print("Engine: {}".format(obj_detect.engine))
    print("Accelerator: {}\n".format(obj_detect.accelerator))
    print("Model:\n{}\n".format(obj_detect.model_id))

    centroid_tracker = edgeiq.CentroidTracker(
        deregister_frames=20, max_distance=50)
    fps = edgeiq.FPS()

    try:

        with edgeiq.WebcamVideoStream(cam=0) as video_stream, \
                edgeiq.Streamer() as streamer:
            # Allow Webcam to warm up
            time.sleep(2.0)
            fps.start()

            # Loop detection and centroid tracker
            while True:
                metrics_manager.newLoop()
                frame = video_stream.read()
                results = obj_detect.detect_objects(frame, confidence_level=.8)

                # Ignore detections of anything other than people
                filter = edgeiq.filter_predictions_by_label(
                    results.predictions, ['person'])

                # Adding info for streamer display
                text = ["Model: {}".format(obj_detect.model_id)]
                text.append(
                    "Inference time: {:1.3f} s".format(results.duration))
                text.append("People currently detected:")

                objects = centroid_tracker.update(filter)

                # Store active predictions for just this loop
                predictions = []
                # Store the active object ids for just this loop

                if len(objects.items()) == 0:
                    # No people detected
                    text.append("-- NONE")

                for (object_id, prediction) in objects.items():
                    metrics_manager.addTimeFor(object_id)
                    timeForId = metrics_manager.timeForId(object_id)
                    # Correcting for fact that index 0 is first object in an array
                    idAdjusted = object_id + 1
                    # Display text with bounding box in video
                    new_label = "Person {i} | {t} sec".format(
                        i=idAdjusted, t=timeForId)
                    prediction.label = new_label
                    text.append(new_label)
                    predictions.append(prediction)

                # Add metrics to text going to streamer
                metrics = metrics_manager.currentMetrics()
                text.append("")  # Spacing
                text.append("Total people seen: {}".format(metrics["count"]))
                text.append("Total time: {} sec".format(metrics["total"]))
                text.append("Average time: {0:.1f} sec".format(metrics["avg"]))
                text.append(
                    "Longest individual time: {} sec".format(metrics["max"]))

                # Update output streamer
                frame = edgeiq.markup_image(frame, predictions)
                streamer.send_data(frame, text)
                fps.update()

                if streamer.check_exit():
                    break

    finally:
        fps.stop()
        print("elapsed time: {:.2f}".format(fps.get_elapsed_seconds()))
        print("approx. FPS: {:.2f}".format(fps.compute_fps()))
        print("Program Ending")


if __name__ == "__main__":
    main()
