import json

import requests
import config
from logger import Log_manager

class User_api:
    def __init__ (self):
        self.token = config.token_user
        self.protocolVersion = config.protocolVersion
        self.sizes = 'smxopqryzw'
        self.logger = Log_manager('User_api')

    def vkget(self, url, params):
        self.logger.log(url, 'getPhotoItems()')
        logtext = ''
        for q in params.keys():
            logtext += f'{q} = {params[q]}; '
        self.logger.log(logtext)
        response = requests.get(url, params = params)
        response = response.json()
        if 'error' in response.keys():
            self.logger.log(f'Ошибка API ВК. Код {response["error"]["error_code"]}: {response["error"]["error_msg"]}', 'vkget()')
            response = {}
        return response

    def userSearch(self, params):
        url = config.vkApiUri + 'users.search'
        params['access_token'] = self.token
        params['v'] = self.protocolVersion
        params['count'] = config.count
        response = self.vkget(url, params=params)

        if response != {}:
            response = response['response']['items']
        return response

    def getFormattedAttachment(self, photo):
        return f"photo{photo['owner_id']}_{photo['id']}_{self.token}"

    def getPhotoItems(self, user_id, album_id = 'profile'):
        params = {
            'owner_id': user_id,
            'album_id': album_id,
            'rev': '0',
            'extended': '1',
            'access_token': self.token,
            'v': self.protocolVersion
        }

        url = config.vkApiUri + 'photos.get'
        photos = self.vkget(url, params = params)
        try:
            photos = photos['response']['items']
        except KeyError:
            photos = []
        for q in range(len(photos)):
            for w in range(len(photos[q]['sizes'])):
                for e in range(len(self.sizes)):
                    if photos[q]['sizes'][w]['type'] == self.sizes[e]:
                        photos[q]['sizes'][w]['sizeIndex'] = e
            currentPhoto = photos[q]['sizes']
            photos[q]['sizes'] = max(currentPhoto, key=lambda currentPhoto: currentPhoto['sizeIndex'])
        self.logger.log(f"Загружено {len(photos)} фотографий пользователя {user_id}", 'getPhotoItems()')
        return photos

    def getPhotoTop(self, user_id, album_id = 'profile'):
        photo_list = self.getPhotoItems(user_id, album_id)
        photo_list = sorted(photo_list, key=lambda photo_list: photo_list['likes']['count'], reverse=True)

        top = []
        q = 0
        while q <= len(photo_list)-1 and q < 3:
            top.append(photo_list[q])
            q += 1
        self.logger.log(f'Составлен топ {len(top)} фотографий пользователя {user_id}', 'getPhotoTop()')
        return top