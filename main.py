import os
import random

import requests
import dotenv


class APIError(Exception):
    pass


class FileError(Exception):
    pass


def get_current_number():
    url = "http://xkcd.com/info.0.json"

    response = requests.get(url)
    response.raise_for_status()

    decoded_response = response.json()

    return decoded_response['num']


def get_random_comics_url(current_number):
    first_number = 1
    random_number = random.randint(first_number, current_number)
    url = f'https://xkcd.com/{random_number}/'

    return url


def get_image_url_with_comment(comics_url):

    url = f'{comics_url}info.0.json'
    response = requests.get(url)
    response.raise_for_status()
    decoded_response = response.json()
    return {
        'image_url': decoded_response['img'],
        'comment': decoded_response['alt']
    }


def save_image(path, image_url):
    response = requests.get(image_url, verify=False)
    response.raise_for_status()
    with open(path, 'wb') as file:
        file.write(response.content)


def check_error_in_response(decoded_response):
    try:
        if decoded_response['error']:
            error_code = decoded_response['error']['error_code']
            error_msg = decoded_response['error']['error_msg']
            raise APIError(f'Error {error_code} - {error_msg}')
    except KeyError:
        pass


def get_upload_url(vk_data):
    url = 'https://api.vk.com/method/photos.getWallUploadServer'
    token, api_version, group_id = vk_data
    payload = {
        'access_token': token,
        'v': api_version,
        'group_id': group_id
    }

    response = requests.get(url, params=payload)
    response.raise_for_status()

    decoded_response = response.json()
    check_error_in_response(decoded_response)

    upload_url = decoded_response['response']['upload_url']

    return upload_url


def upload_photo_and_get_response(photo_path, upload_url):

    with open(photo_path, 'rb') as file:
        files = {
            'photo': file,
        }
        upload_photo_response = requests.post(upload_url, files=files)
    upload_photo_response.raise_for_status()

    decoded_response = upload_photo_response.json()
    check_error_in_response(decoded_response)

    return decoded_response


def save_photo_and_return_attachments(token, api_version, group_id, upload_response):
    url = 'https://api.vk.com/method/photos.saveWallPhoto'
    payload = upload_response
    payload.update({
        'access_token': token,
        'v': api_version,
        'group_id': group_id
    })

    response = requests.post(url, params=payload)
    response.raise_for_status()

    decoded_response = response.json()
    check_error_in_response(decoded_response)

    media_id = decoded_response['response'][0]['id']
    owner_id = decoded_response['response'][0]['owner_id']

    return f'photo{owner_id}_{media_id}'


def post_photo(token, api_version, group_id, attachments, message):
    url = 'https://api.vk.com/method/wall.post'
    payload = {
        'access_token': token,
        'v': api_version,
        'from_group': 1,
        'owner_id': f'-{group_id}',
        'attachments': attachments,
        'message': message
    }

    response = requests.get(url, params=payload)
    response.raise_for_status()

    decoded_response = response.json()
    check_error_in_response(decoded_response)

    return decoded_response


def delete_file(path):
    try:
        os.remove(path)
    except OSError as e:
        raise FileError(f"Error: {e.filename} - {e.strerror}")


if __name__ == '__main__':

    dotenv.load_dotenv()

    vk_client_id = os.getenv('VK_CLIENT_ID')
    vk_access_token = os.getenv('VK_ACCESS_TOKEN')
    vk_api_version = os.getenv('VK_API_VERSION')
    vk_group_id = os.getenv('VK_GROUP_ID')

    vk_data = [vk_access_token, vk_api_version, vk_group_id]

    comics_url = get_random_comics_url(get_current_number())

    image_url, image_comment = get_image_url_with_comment(comics_url).values()
    image_name = image_url.split('/')[-1]

    path = f'./{image_name}'

    save_image(path, image_url)

    upload_photo_url = get_upload_url(vk_data)

    upload_photo_response = upload_photo_and_get_response(path, upload_photo_url)

    attachments = save_photo_and_return_attachments(vk_access_token, vk_api_version, vk_group_id, upload_photo_response)

    post_photo(vk_access_token, vk_api_version, vk_group_id, attachments, image_comment)

    delete_file(path)
