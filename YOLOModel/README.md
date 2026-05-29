

***

## 🛠️ Installation & Setup Guide

To ensure everyone can run this project smoothly and avoid environment conflicts across different computers, we highly recommend setting up the project using a Python **virtual environment**. Please follow these detailed steps:

### Step 1: Create and Activate a Virtual Environment

1. **Open Terminal / Command Prompt:** Navigate to the root directory of this project (the folder containing `pythoncv.py`).

2. **Create the virtual environment:**
   Enter the following command in your terminal. This will create an isolated environment named `venv` in your current folder:
   * **Mac / Linux:** ```bash
     python3 -m venv venv
     ```
   * **Windows:** ```bash
     python -m venv venv
     ```

3. **Activate the virtual environment (CRITICAL❗️):**
   The libraries you install will only be placed in this isolated environment *after* activation. Run the corresponding command for your operating system:
   * **Mac / Linux:** ```bash
     source venv/bin/activate
     ```
   * **Windows:** ```bash
     venv\Scripts\activate
     ```
   > ✅ **Success Indicator:** Once successfully activated, you will see `(venv)` at the very beginning of your command prompt.

### Step 2: Install Required Dependencies

While ensuring your virtual environment is **activated** (the terminal shows the `(venv)` prefix), we need to install the libraries related to computer vision and the backend server.

Copy and run the following command in your terminal to install all required libraries at once:
```bash
pip install opencv-python ultralytics fastapi uvicorn
```
*Library breakdown:*
* `opencv-python`: Used for reading video frames and drawing on images.
* `ultralytics`: The official YOLOv8 library, used for the core people/object detection.
* `fastapi` & `uvicorn`: Used to build a lightweight backend to stream video and send data to the frontend.

### Step 3: Run the Application (Backend & Frontend)

1. **Prepare your video file:**
   Please make sure your test video file (e.g., `demo_video01.MOV` as specified in the code) is placed in the **same folder** as `pythoncv.py`.

2. **Start the Python backend:**
   Run the following command in your terminal (while keeping the virtual environment activated):
   ```bash
   python3 pythoncv.py
   ```
   > ⏳ **Note:** The first time you run this command, the system will automatically download the lightweight YOLOv8 model file (`yolov8n.pt`). This might take anywhere from a few seconds to a minute, so please be patient. When you see a message like `Uvicorn running on http://0.0.0.0:8000` in the terminal, the backend has successfully started!

3. **Open the frontend interface:**
   Keep the backend running (do not close the terminal). Open your file manager, locate the `Frontend_index.html` file in the project folder, and **double-click it** to open it directly in your web browser.
   
   You should now be able to see the real-time monitoring feed, the current number of detected people, and a historical trend chart showing how the headcount changes over time! 🎉

***


To check the demo_video or camera:

http://localhost:8001/video_feed/area_225_2f_1
http://localhost:8001/video_feed/area_225_2f_2
http://localhost:8001/video_feed/area_225_2f_3
http://localhost:8001/video_feed/area_225_2f_4

