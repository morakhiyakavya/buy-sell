from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import cv2
import numpy as np
import typing
from pathlib import Path
# Try to import the optional ML/ONNX modules. If they are unavailable
# (e.g. missing onnxruntime DLLs) fall back to stubs so the Flask app
# can still import and run other endpoints.
ML_AVAILABLE = True
try:
    from mltu.utils.text_utils import ctc_decoder, get_cer
    from mltu.configs import BaseModelConfigs
    from mltu.inferenceModel import OnnxInferenceModel
except Exception:
    ML_AVAILABLE = False
    # Minimal stubs to allow imports; actual captcha prediction will
    # return a safe default when ML isn't available.
    def ctc_decoder(preds, vocab):
        return [""]

    def get_cer(a, b):
        return 1.0

    class BaseModelConfigs:
        @staticmethod
        def load(path):
            raise RuntimeError("ML configs not available in this environment")

    class OnnxInferenceModel:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("OnnxInferenceModel not available in this environment")

# Changes are needed here
current_directory = Path(__file__).resolve().parent
class ImageToWordModel(OnnxInferenceModel):
    def __init__(self, char_list: typing.Union[str, list], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.char_list = char_list

        # Get these directly from the loaded ONNX model
        model_input = self.model.get_inputs()[0]
        self.input_name = model_input.name
        self.input_shape = model_input.shape

        print(f"Model input name: {self.input_name}")
        print(f"Model input shape: {self.input_shape}")

    def predict(self, image: np.ndarray):

        print("Predict received:", image.shape)

        height = int(self.input_shape[1])
        width = int(self.input_shape[2])

        image = cv2.resize(image, (width, height))
        print("After resize:", image.shape)

        image_pred = np.expand_dims(image, axis=0).astype(np.float32)

        preds = self.model.run(
            None,
            {self.input_name: image_pred}
        )[0]

        text = ctc_decoder(preds, self.char_list)[0]

        return text

def predict_captcha(driver=None, image_type=None, image_path=None):
    try:
        if not ML_AVAILABLE:
            print("predict_captcha: ML runtime unavailable, returning empty prediction")
            return ""

        # ---------------------------------------------------------
        # 1. Get image either from a supplied path or from Selenium
        # ---------------------------------------------------------
        if image_path:
            img = os.path.abspath(image_path)

            if not os.path.exists(img):
                raise FileNotFoundError(f"Captcha image not found: {img}")

            print(f"Reading captcha from: {img}")

        elif driver is not None:
            if image_type == "bigshare":
                captcha = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "captcha"))
                )

            elif image_type == "kfintech":
                captcha = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "captchaimg"))
                )

            else:
                raise ValueError("Unknown image type")

            img = os.path.join(current_directory, "captcha.png")

            captcha.screenshot(img)

            print(f"Captcha screenshot saved to: {img}")

        else:
            raise ValueError(
                "Either 'driver' or 'image_path' must be provided"
            )

        # ---------------------------------------------------------
        # 2. Load image
        # ---------------------------------------------------------
        image = cv2.imread(img)

        if image is None:
            raise ValueError(f"OpenCV could not read image: {img}")

        print("Original image shape:", image.shape)

        # ---------------------------------------------------------
        # 3. Load appropriate captcha model
        # ---------------------------------------------------------
        if image_type == "bigshare":

            config_path = os.path.join(
                current_directory,
                "trial_bigshare",
                "configs.yaml"
            )

            configs_bigshare = BaseModelConfigs.load(config_path)

            configs_directory = os.path.dirname(config_path)

            model_absolute_path = os.path.join(
                configs_directory,
                configs_bigshare.model_path
            )

            if not os.path.exists(model_absolute_path):
                raise FileNotFoundError(
                    f"The model file was not found at {model_absolute_path}"
                )

            model = ImageToWordModel(
                model_path=model_absolute_path,
                char_list=configs_bigshare.vocab
            )

            final_image = image

        elif image_type == "kfintech":

            final_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            print("Gray image shape:", final_image.shape)

            config_path = os.path.join(
                current_directory,
                "trial_kfintech",
                "configs.yaml"
            )

            configs_kfintech = BaseModelConfigs.load(config_path)

            configs_directory = os.path.dirname(config_path)

            model_absolute_path = os.path.join(
                configs_directory,
                configs_kfintech.model_path
            )

            if not os.path.exists(model_absolute_path):
                raise FileNotFoundError(
                    f"The model file was not found at {model_absolute_path}"
                )

            model = ImageToWordModel(
                model_path=model_absolute_path,
                char_list=configs_kfintech.vocab
            )

        else:
            raise ValueError(
                "image_type must be either 'bigshare' or 'kfintech'"
            )

        # ---------------------------------------------------------
        # 4. Convert grayscale images to 3 channels
        # ---------------------------------------------------------
        image = (
            np.stack((final_image,) * 3, axis=-1)
            if final_image.ndim == 2
            else final_image
        )
        print("Model input image shape:", image.shape)

        # ---------------------------------------------------------
        # 5. Predict
        # ---------------------------------------------------------
        prediction_text = model.predict(image)

        print(f"Prediction: {prediction_text}")

        return prediction_text

    except Exception as e:
        print(f"Error in predict_captcha: {e}")
        return ""
