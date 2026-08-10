import cv2
import time
from ultralytics import YOLO

# 1. Load the lightweight YOLO model (downloads automatically the first time)
# "n" stands for nano (fastest, best for Raspberry Pi)
model = YOLO("yolo11n.pt") 

# 2. Open the default webcam (0 is usually the built-in webcam)
cap = cv2.VideoCapture(0)

print("Starter YOLO-AI... Tryk 'q' på tastaturet for at afslutte.")

while True:
    # Start timer to control our 1 FPS limit
    start_time = time.time()
    
    # 3. Read ONE frame from the webcam
    ret, frame = cap.read()
    if not ret:
        print("Kunne ikke læse fra kameraet!")
        break
        
    # 4. Run the AI on that single frame (looking for humans, cats, dogs, etc.)
    # verbose=False keeps the terminal clean
    results = model(frame, verbose=False) 
    
    # 5. Draw boxes on the image and show it in a window
    annotated_frame = results[0].plot()
    cv2.imshow("YOLO 1 FPS Test", annotated_frame)
    
    # 6. Check if user pressed 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
        
    # 7. Sleep to force exactly 1 frame per second (1 FPS)
    time_to_sleep = 0.01 - (time.time() - start_time)
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)

# Cleanup
cap.release()
cv2.destroyAllWindows()