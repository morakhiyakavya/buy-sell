from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import cv2
import numpy as np
import typing
from PIL import Image, ImageEnhance
from skimage import exposure
from mltu.utils.text_utils import ctc_decoder, get_cer
from mltu.configs import BaseModelConfigs
from mltu.inferenceModel import OnnxInferenceModel

# Changes are needed here
current_directory = 'C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app'
class ImageToWordModel(OnnxInferenceModel):
    def __init__(self, char_list: typing.Union[str, list], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.char_list = char_list

    def predict(self, image: np.ndarray):
        image = cv2.resize(image, self.input_shape[:2][::-1])

        image_pred = np.expand_dims(image, axis=0).astype(np.float32)

        preds = self.model.run(None, {self.input_name: image_pred})[0]

        text = ctc_decoder(preds, self.char_list)[0]

        return text




def predict_captcha(driver,image_type):
    try:

        """
        Capture the image from respective args based website and predict the text.
        
        Args:
        - driver (WebDriver): The Current Working Selenium WebDriver instance
        - image_type (str): The type of the image ('kfintech' or 'bigshare')
        
        Returns:
        - str: The predicted text
        """
        # Assuming these are your model initialization lines adjusted for both models
        if image_type == 'bigshare':
            captcha = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "captcha")))
        elif image_type == 'kfintech':
            captcha = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'captchaimg')))
        image = captcha.screenshot(os.path.join(current_directory, f'captcha.png'))
        img = os.path.join(current_directory, f'captcha.png')

        # Load the image.
        image = cv2.imread(img)
        final_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if image_type == 'bigshare':
            # big = 'C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\trial_bigshare\\configs.yaml'
            big = os.path.join(current_directory, 'trial_bigshare', 'configs.yaml')
            configs_bigshare = BaseModelConfigs.load(big)
            
            #try to get the model path from the configs.yaml file
            configs_directory = os.path.dirname(big)
            model_relative_path = configs_bigshare.model_path
            model_absolute_path = os.path.join(configs_directory, model_relative_path)
            # Now use model_absolute_path when loading the model
            if not os.path.exists(model_absolute_path):
                raise FileNotFoundError(f"The model file was not found at {model_absolute_path}")
            model_bigshare = ImageToWordModel(model_path=model_absolute_path, char_list=configs_bigshare.vocab)

            # model_bigshare = ImageToWordModel(model_path=configs_bigshare.model_path, char_list=configs_bigshare.vocab)

            equalized_array = exposure.equalize_adapthist(final_image / 255.0, clip_limit=0.03) * 255
            # Since equalize_adapthist outputs float64, we need to convert it back to uint8
            equalized_image_cv = np.uint8(equalized_array)

            thresh = cv2.adaptiveThreshold(equalized_image_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            final_image = Image.fromarray(thresh)
            
            enhancer = ImageEnhance.Contrast(final_image)
            final_image = enhancer.enhance(2.0)
            model = model_bigshare
        elif image_type == 'kfintech':
            kfin = os.path.join(current_directory,'trial_kfintech','configs.yaml')
            configs_kfintech = BaseModelConfigs.load(kfin)
            #try to get the model path from the configs.yaml file
            configs_directory = os.path.dirname(kfin)
            model_relative_path = configs_kfintech.model_path
            model_absolute_path = os.path.join(configs_directory, model_relative_path)
            # Now use model_absolute_path when loading the model
            if not os.path.exists(model_absolute_path):
                raise FileNotFoundError(f"The model file was not found at {model_absolute_path}")
            model_kfintech = ImageToWordModel(model_path=model_absolute_path, char_list=configs_kfintech.vocab)

            # model_kfintech = ImageToWordModel(model_path=configs_kfintech.model_path, char_list=configs_kfintech.vocab)
            model = model_kfintech
        else:
            raise ValueError("Unknown image type")

        image = np.stack((final_image,)*3, axis=-1)
        # Assuming preprocessing is done within the model's predict method or before this line
        prediction_text = model.predict(image)

        return prediction_text
    except Exception as e:
        print(f"Error in predict_captcha: {e}")
        raise