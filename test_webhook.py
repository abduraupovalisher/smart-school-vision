import requests


def test_webhook():
    url = "http://localhost:8000/api/webhook"

    xml_data = "<EventNotificationAlert><employeeNoString>12345</employeeNoString></EventNotificationAlert>"
    image_data = b"dummy image data"

    # We use arbitrary field names because the backend iterates through all form items
    # and checks the content_type of the UploadFiles.
    files = {
        "xml_file": ("event.xml", xml_data, "text/xml"),
        "image_file": ("snapshot.jpg", image_data, "image/jpeg"),
    }

    print(f"Sending POST request to {url}...")
    try:
        response = requests.post(url, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_webhook()
