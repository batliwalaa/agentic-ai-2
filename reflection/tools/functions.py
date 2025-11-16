from datetime import datetime

def get_current_time() -> str:
    """Returns the current date and time as a string."""
    return datetime.now().strftime("%H:%M:%S")


import requests

def get_weather_from_ip() -> str:
    """
    Gets the current, high, and low temperature in Fahrenheit for the user's
    location and returns it to the user.
    """
    # Get location coordinates from the IP address
    lat, lon = requests.get("https://ipinfo.io/json").json()["loc"].split(",")

    # Set parameters for the weather API call
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }
    # Call the weather API
    weather_response = requests.get("https://api.open-meteo.com/v1/forecast", params=params).json()

    #format and return the weather information
    current_temp = weather_response["current"]["temperature_2m"]
    high_temp = weather_response["daily"]["temperature_2m_max"][0]
    low_temp = weather_response["daily"]["temperature_2m_min"][0]

    return (f"The current temperature is {current_temp}°F, "
            f"with a high of {high_temp}°F and a low of {low_temp}°F today.")


import qrcode
from qrcode.image.styledpil import StyledPilImage

def generate_qr_code(data: str, filename: str, image_path: str) -> str:
    """
    Generates a QR code for the given data and saves it as an image file.
    Args:
        data: The data to encode in the QR code.
        filename: The name of the output image file (without extension).
        image_path: The path to save the image file.
    """
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H)
    
    qr.add_data(data)

    img = qr.make_image(image_factory=StyledPilImage, embedded_image_path=image_path)
    output_file = f"{filename}.png"
    img.save(output_file)

    return f"QR code saved as {output_file} containing: {data[:50]}..."

def write_text_to_file(content: str, file_path: str) -> str:
    """
    Writes the given text to a file with the specified filename.
    Args:
        content: The text content to write to the file.
        file_path (str): Destination path.
    """
    
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    
    return file_path

