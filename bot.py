from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import datetime
from db import Bot_database
import config
from vk_user_api import User_api
from logger import Log_manager
import hardcoded_dict

class Bot:
    def __init__(self, token_group):
        self.session = vk_api.VkApi(token=token_group)
        self.users = {}
        self.userCandidates = {}
        self.logger = Log_manager('Bot')

        self.readMessages()

    def write_msg(self, user_id, message, attachment=None):
        params = {
            'user_id': user_id,
            'message': message,
            'random_id': randrange(10 ** 7)
        }
        if self.users[user_id].statusOfExpectation == 0:
            keyboard = VkKeyboard(one_time=False)
            keyboard.add_button(hardcoded_dict.dictionary['commands']['find_candidates'], VkKeyboardColor.POSITIVE)
            params['keyboard'] = keyboard.get_keyboard()
        if self.users[user_id].statusOfExpectation == 1:
            keyboard = VkKeyboard(one_time=False)
            keyboard.add_button(hardcoded_dict.dictionary['commands']['like'], VkKeyboardColor.POSITIVE)
            keyboard.add_button(hardcoded_dict.dictionary['commands']['next'], VkKeyboardColor.SECONDARY)
            keyboard.add_button(hardcoded_dict.dictionary['commands']['set_preferences'], VkKeyboardColor.POSITIVE)
            params['keyboard'] = keyboard.get_keyboard()
        if self.users[user_id].statusOfExpectation == 4:
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('1')
            keyboard.add_button('2')
            keyboard.add_button(hardcoded_dict.dictionary['commands']['preference_id_nullable'], VkKeyboardColor.SECONDARY)
            params['keyboard'] = keyboard.get_keyboard()
        if self.users[user_id].statusOfExpectation == 5:
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button(hardcoded_dict.dictionary['commands']['preference_id_nullable'], VkKeyboardColor.SECONDARY)
            params['keyboard'] = keyboard.get_keyboard()
        if self.users[user_id].statusOfExpectation == 6:
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('1')
            keyboard.add_button('2')
            params['keyboard'] = keyboard.get_keyboard()

        if attachment != None:
            params['attachment'] = attachment
        try:
            self.session.method('messages.send', params)
            self.logger.log(f'Пользователю {user_id} отправлено сообщение "{message}"', 'write_msg()')
        except vk_api.exceptions.ApiError:
            self.logger.log(f'Не удалось отправить сообщение пользователю {user_id}', 'write_msg()')

    '''Выставляет статус, в котором находится пользователь (какой ответ бот ждёт от него)'''
    def setStatusOfExpectation(self, user, state):
        maritals_list = ''
        for q in hardcoded_dict.dictionary['marital_status'].keys():
            maritals_list += str(q) + " - " + hardcoded_dict.dictionary['marital_status'][q] + '\n'

        phrases = {
            2: f"Введи возраст, с которого будет искать кандидата.\n{hardcoded_dict.dictionary['commands']['preference_id_nullable']} - если не имеет значения.",
            3: 'Укажи возраст, в пределах которого ты ищешь кандидата.',
            4: f'Укажи пол кандидата, которого ищешь.\n1 - Женщина\n2 - Мужчина\n{hardcoded_dict.dictionary["commands"]["preference_id_nullable"]} - если не имеет значения',
            5: 'Теперь укажи семейное положение искомого кандидата\n' + maritals_list + f'{hardcoded_dict.dictionary["commands"]["preference_id_nullable"]} - если не имеет значения',
            6: 'Ты планируешь искать только в своём городе, или по всей стране?\n1 - только в моём городе\n2 - по всей стране'
        }

        if state == 5 and user.id in self.userCandidates.keys():
            del self.userCandidates[user.id]

        if state == 1:
            user.statusOfExpectation = state
        else:
            if state in hardcoded_dict.dictionary['status_of_expectation'].keys():
                user.statusOfExpectation = state
                self.logger.log(f"Пользователь {user.id} {user.name} в статусе {hardcoded_dict.dictionary['status_of_expectation'][state]}", 'setStatusOfExpectation()')
                if user.haveRegistration == False and state == 2:
                    self.write_msg(user.id, 'Хорошо, но сперва нам нужно понять, кого ты ищешь.')
                    self.write_msg(user.id, phrases[state])
                else:
                    if state in phrases.keys():
                        self.write_msg(user.id, phrases[state])
                    else:
                        self.logger.log(f'Нет подходящей фразы для статуса {state}', 'setStatusOfExpectation()')
            else:
                self.logger.log(f'Передан неизвестный статус пользователя {state}.', 'setStatusOfExpectation()')

    '''Cоставляет список кандидатов для юзера'''
    def getCandidates(self, user):
        params = {
            'sort': 0
        }
        if user.preferences['city_id'] != None:
            params['city_id'] = user.preferences['city_id']
        if user.preferences['age_from'] != None:
            params['age_from'] = user.preferences['age_from']
        if user.preferences['age_to'] != None:
            params['age_to'] = user.preferences['age_to']
        if user.preferences['sex_id'] != None:
            params['sex'] = user.preferences['sex_id']
        if user.preferences['marital_status'] != None:
            params['status'] = user.preferences['marital_status']
        if user.offset > 0:
            params['offset'] = user.offset

        if user.id not in self.userCandidates.keys():
            self.userCandidates[user.id] = []

        self.write_msg(user.id, 'Подожди, я составляю список людей')

        candidates = User_api().userSearch(params)
        if candidates != {}:
            for q in candidates:
                self.userCandidates[user.id].append(
                    Vk_account(q['id'], self.session)
                )
            response = True
            user.offset += 1
        else:
            self.logger.log(f'Не удалось загрузить список кандидатов с параметрами, выбранными для {user.id}.')
            response = False
        return response

    '''Отправляет пользователю следующего кандидата'''
    def sendNextCandidate(self, user):
        haveCandidate = False
        userListReady = True

        if user.id not in self.userCandidates.keys():
            userListReady = self.getCandidates(self.users[user.id])

        if userListReady:
            for q in range(len(self.userCandidates[user.id])):
                if user.haveRelation(self.userCandidates[user.id][q]) == False:
                    if len(self.userCandidates[user.id][q].photos) > 0:
                        candidate = self.userCandidates[user.id][q]

                        haveCandidate = True

                        attachments = []
                        for w in self.userCandidates[user.id][q].photos:
                            w = User_api().getFormattedAttachment(w)
                            attachments.append(w)
                        attachments = ','.join(attachments)
                        self.logger.log('Подготовлены вложения: '+attachments, 'sendNextCandidate()')

                        text = f'Нашли кое-кого для тебя!\n{candidate.name}\nВозраст: {candidate.age}\nСсылка на профиль: {candidate.url}'
                        self.write_msg(user.id, text, attachments)
                        self.write_msg(user.id, f'Введи:\n{hardcoded_dict.dictionary["commands"]["like"]} - если тебе нравится;\n{hardcoded_dict.dictionary["commands"]["next"]} - если не нравится') #{hardcoded_dict.dictionary["commands"]["favorite"]} - если хочешь добавить в избранное;\n
                        user.setRelation(candidate.id)
                        if user.statusOfExpectation != 1:
                            self.setStatusOfExpectation(user, 1)
                        break
                    else:
                        continue
                else:
                    continue
            if haveCandidate == False:
                self.write_msg(user.id, 'Прости, но похоже ты посмотрел всех кандидатов по твоим параметрам. Измени параметры поиска или приходи в другой раз.')
                del self.userCandidates[user.id]
        return haveCandidate


    def readMessages(self):
        longpoll = VkLongPoll(self.session)
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    request = event.text.lower()

                    if event.user_id not in self.users.keys():
                        self.users[event.user_id] = Vk_account(event.user_id, self.session)
                    self.logger.log(f'Пользователь {event.user_id} {self.users[event.user_id].name} написал: "{request}"', 'readMessages()')

                    if self.users[event.user_id].banStatus:
                        self.write_msg(event.user_id, f'Прости, {self.users[event.user_id].name}, но, похоже, ты в бане =(')
                    else:
                        self.logger.log(f'statusOfExpectation пользователя {event.user_id} - {self.users[event.user_id].statusOfExpectation}')

                        '''Если пользователь вводит возраст "С" '''
                        if self.users[event.user_id].statusOfExpectation == 2:
                            if request == hardcoded_dict.dictionary['commands']['preference_id_nullable'].lower():
                                self.users[event.user_id].preferences['age_from'] = 18
                                self.setStatusOfExpectation(self.users[event.user_id], 3)
                                
                            else:
                                try:
                                    int(request)
                                except ValueError:
                                    self.write_msg(event.user_id, 'Упс! Что-то это не похоже на число.')
                                else:
                                    if int(request) < 18:
                                        self.write_msg(event.user_id, 'А тебе обязательно искать кого-то настолько молодого?')
                                    else:
                                        if int(request) > 100:
                                            self.write_msg(event.user_id, 'Я что, похож на музей?')
                                        else:
                                            self.users[event.user_id].preferences['age_from'] = int(request)
                                            self.setStatusOfExpectation(self.users[event.user_id], 3)
                                            
                            continue

                        '''Если пользователь вводит возраст "ПО" '''
                        if self.users[event.user_id].statusOfExpectation == 3:
                            if request == hardcoded_dict.dictionary['commands']['preference_id_nullable'].lower():
                                self.users[event.user_id].preferences['age_to'] = None
                                self.setStatusOfExpectation(self.users[event.user_id], 4)
                                
                            else:
                                try:
                                    int(request)
                                except ValueError:
                                    self.write_msg(event.user_id, 'Упс! Что-то это не похоже на число.')
                                else:
                                    if int(request) < 16:
                                        self.write_msg(event.user_id, 'А тебе обязательно искать кого-то настолько молодого?')
                                    else:
                                        if int(request) > 100:
                                            self.users[event.user_id].preferences['age_to'] = None
                                            self.setStatusOfExpectation(self.users[event.user_id], 4)
                                            
                                        else:
                                            if self.users[event.user_id].preferences['age_from'] == None:
                                                self.users[event.user_id].preferences['age_to'] = int(request)
                                                self.setStatusOfExpectation(self.users[event.user_id], 4)
                                                
                                            else:
                                                if int(request) < self.users[event.user_id].preferences['age_from']:
                                                    self.write_msg(event.user_id, f'Возраст "ПО" не может быть меньше {self.users[event.user_id].preferences["age_from"]}')
                                                else:
                                                    self.users[event.user_id].preferences['age_to'] = int(request)
                                                    self.setStatusOfExpectation(self.users[event.user_id], 4)
                            continue

                        '''Если пользователь вводит пол'''
                        if self.users[event.user_id].statusOfExpectation == 4:
                            maritals_list = ''
                            for q in hardcoded_dict.dictionary['marital_status'].keys():
                                maritals_list += str(q) + " - " + hardcoded_dict.dictionary['marital_status'][q] + '\n'

                            if request == hardcoded_dict.dictionary['commands']['preference_id_nullable'].lower():
                                self.users[event.user_id].preferences['sex_id'] = None
                                self.setStatusOfExpectation(self.users[event.user_id], 5)
                                continue
                            else:
                                try:
                                    int(request)
                                except ValueError:
                                    self.write_msg(event.user_id, f'Укажи 1 (Женщина), 2 (Мужичина) или {hardcoded_dict.dictionary["commands"]["preference_id_nullable"]}')
                                    continue
                                else:
                                    try:
                                        hardcoded_dict.dictionary['sex_id'][int(request)]
                                    except KeyError:
                                        self.write_msg(event.user_id, f'Укажи 1 (Женщина), 2 (Мужичина) или {hardcoded_dict.dictionary["commands"]["preference_id_nullable"]}')
                                        continue
                                    else:
                                        self.users[event.user_id].preferences['sex_id'] = int(request)
                                        self.setStatusOfExpectation(self.users[event.user_id], 5)
                            continue

                        '''Если пользователь указывает семейное положение'''
                        if self.users[event.user_id].statusOfExpectation == 5:
                            if request == hardcoded_dict.dictionary['commands']['preference_id_nullable'].lower():
                                self.users[event.user_id].preferences['marital_status'] = None
                                if self.users[event.user_id].city == None:
                                    self.write_msg(event.user_id, 'В твоём профиле не указан город, поэтому кандидаты будут со всего ВК. Укажи город в своём профиле, и напиши "предпочтения", чтобы указать параметры кандидата заново.')
                                    self.users[event.user_id].saveVKAccountAsUser()
                                    self.setStatusOfExpectation(self.users[event.user_id], 1)
                                    self.sendNextCandidate(self.users[event.user_id])
                                else:
                                    self.setStatusOfExpectation(self.users[event.user_id], 6)

                            else:
                                try:
                                    int(request)
                                except ValueError:
                                    self.write_msg(event.user_id, 'Укажи вариант семейного положения от 0 до 8')
                                else:
                                    try:
                                        hardcoded_dict.dictionary['marital_status'][int(request)]
                                    except KeyError:
                                        self.write_msg(event.user_id, 'Укажи вариант семейного положения от 0 до 8')
                                    else:
                                        self.users[event.user_id].preferences['marital_status'] = int(request)
                                        if self.users[event.user_id].city == None:
                                            self.write_msg(event.user_id, 'В твоём профиле не указан город, поэтому кандидаты будут со всего ВК. Укажи город в своём профиле, и напиши "предпочтения", чтобы указать параметры кандидата заново.')
                                            self.users[event.user_id].saveVKAccountAsUser()
                                            self.setStatusOfExpectation(self.users[event.user_id], 1)
                                            self.sendNextCandidate(self.users[event.user_id])
                                        else:
                                            self.setStatusOfExpectation(self.users[event.user_id], 6)
                            continue

                        '''Когда пользователь указывает, в своем ли городе он ищет кандидата'''
                        if self.users[event.user_id].statusOfExpectation == 6:
                            try:
                                int(request)
                            except ValueError:
                                self.write_msg(event.user_id, '1 - только в моём городе\n2 - по всей стране')
                                continue
                            else:
                                if int(request) == 1:
                                    self.users[event.user_id].preferences['city_id'] = self.users[event.user_id].city
                                    self.users[event.user_id].saveVKAccountAsUser()
                                    self.setStatusOfExpectation(self.users[event.user_id], 1)
                                    self.sendNextCandidate(self.users[event.user_id])
                                    continue
                                elif int(request) == 2:
                                    self.users[event.user_id].preferences['city_id'] = None
                                    self.users[event.user_id].saveVKAccountAsUser()
                                    self.setStatusOfExpectation(self.users[event.user_id], 1)
                                    self.sendNextCandidate(self.users[event.user_id])
                                    continue
                                else:
                                    self.write_msg(event.user_id, '1 - только в моём городе\n2 - по всей стране')
                            continue

                        if request in (hardcoded_dict.dictionary["commands"]["like"].lower(), hardcoded_dict.dictionary["commands"]["next"].lower(), hardcoded_dict.dictionary["commands"]["favorite"].lower()):
                            if self.users[event.user_id].haveRelation:
                                if request == hardcoded_dict.dictionary["commands"]["like"].lower():
                                    self.setStatusOfExpectation(self.users[event.user_id], 1)
                                    self.users[event.user_id].setRelation(relation=True)
                                    self.sendNextCandidate(self.users[event.user_id])
                                elif request == hardcoded_dict.dictionary["commands"]["next"].lower():
                                    self.setStatusOfExpectation(self.users[event.user_id], 1)
                                    self.users[event.user_id].setRelation(relation=False)
                                    self.sendNextCandidate(self.users[event.user_id])
                                else:
                                    self.setStatusOfExpectation(self.users[event.user_id], 1)
                                    self.users[event.user_id].setRelation(relation=True, is_favorite=True)
                                    self.sendNextCandidate(self.users[event.user_id])
                            else:
                                self.write_msg(event.user_id, 'Упс! Мне не ясно, кому ты хочешь оставить реакцию.')
                                self.setStatusOfExpectation(self.users[event.user_id], 1)



                        if request == hardcoded_dict.dictionary['commands']['find_candidates'].lower():
                            self.setStatusOfExpectation(self.users[event.user_id], 1)
                            self.sendNextCandidate(self.users[event.user_id])
                            continue

                        if request == hardcoded_dict.dictionary['commands']['set_preferences'].lower():
                            self.setStatusOfExpectation(self.users[event.user_id], 2)
                            continue

                        if self.users[event.user_id].haveRegistration == False:
                            self.write_msg(event.user_id, 'давай знакомиться!')
                            self.setStatusOfExpectation(self.users[event.user_id], 2)
                            continue

                   

class Vk_account:
    def __init__(self, user_id, session):
        self.logger = Log_manager('Vk_account')
        self.logger.log(f'Пользователь {user_id}', '__init__')

        self.id = user_id
        self.name = None
        self.age = None
        self.sex = None
        self.marital_status = None
        self.city = None
        self.banStatus = None
        self.haveRegistration = None
        self.url = config.vkProd + 'id' + str(self.id)
        self.photos = User_api().getPhotoTop(self.id)
        self.statusOfExpectation = 0
        self.offset = 0

        '''Время, когда бот запомнил пользователя в оперативной памяти. Нужно для периодической чистки по расписанию'''
        self.timeRemembering = datetime.datetime.now()

        self.getAccountData(session)
        self.getBanStatus()
        self.getRegistrationStatus()
        if  self.haveRegistration:
            self.getPreferences()
        else:
            self.preferences = {}
            self.preferences['age_from'] = 18
            if self.age != None:
                self.preferences['age_to'] = self.age
            else:
                self.preferences['age_to'] = None
            if self.sex != None:
                if self.sex == 1:
                    self.preferences['sex_id'] = 2
                else:
                    self.preferences['sex_id'] = 1
            else:
                self.preferences['sex_id'] = None
            self.preferences['marital_status'] = 6
            if self.city != None:
                self.preferences['city_id'] = self.city
            else:
                self.preferences['city_id'] = None
            self.saveVKAccountAsUser()

        if self.banStatus != True:
            self.saveVKAccountAsAccount()

    def getAccountData(self, session):
        account_data = session.method('users.get', {'user_id': self.id, 'fields': 'relation, sex, bdate, city'})
        if len(account_data) > 0:
            account_data = account_data[0]
            try:
                self.name = account_data['first_name'] + ' ' + account_data['last_name']
            except KeyError:
                self.logger.log(f'Имя пользователя {self.id}: {self.name} неизвестно.', 'getAccountData()')
            try:
                bDate = account_data['bdate'].split('.')
                if len(bDate) == 3:
                    bDate = datetime.datetime(int(bDate[2]), int(bDate[1]), int(bDate[0]))
                    age = datetime.datetime.now() - bDate
                    self.age = int(age.days / 365)
            except KeyError:
                self.logger.log(f'Дата рождения пользователя {self.id}: {self.name} неизвестна.', 'getAccountData()')
            try:
                self.sex = account_data['sex']
            except KeyError:
                self.logger.log(f'Пол пользователя {self.id}: {self.name} неизвестен.', 'getAccountData()')
            try:
                self.marital_status = account_data['relation']
            except KeyError:
                self.logger.log(f'Семейное положение пользователя {self.id}: {self.name} неизвестно.', 'getAccountData()')
            try:
                self.city = account_data['city']['id']
            except KeyError:
                self.logger.log(f'Город пользователя {self.id}: {self.name} неизвестен.', 'getAccountData()')

            messageAboutUser = f'Загружены данные пользователя ID {self.id}'
            if self.name != None:
                messageAboutUser += f', имя - {self.name}'
            if self.age != None:
                messageAboutUser += f', возраст - {self.age}'
            if self.sex != None:
                messageAboutUser += f", пол - {hardcoded_dict.dictionary['sex_id'][self.sex]}"
            if self.marital_status != None:
                messageAboutUser += f", семейное положение - {hardcoded_dict.dictionary['marital_status'][self.marital_status]}"

            self.logger.log(messageAboutUser, 'getAccountData()')
        else:
            account_data = None
        return account_data

    def saveVKAccountAsAccount(self):
        Bot_database().addAccount(self.id)
        return id

    def getBanStatus(self):
        self.banStatus = Bot_database().isBanned(self.id)
        return self.banStatus

    def getRegistrationStatus(self):
        id = Bot_database().idByExternal(self.id)
        if id[1] != None:
            response = True
        else:
            response = False
        self.haveRegistration = response
        return self.haveRegistration

    def saveVKAccountAsUser(self):
        return Bot_database().addUser(self.id, self.preferences["age_from"], self.preferences['age_to'], self.preferences['sex_id'], self.preferences['city_id'], self.preferences['marital_status'])

    def getPreferences(self):
        preferences = Bot_database().getPreferences(self.id)
        if preferences == None:
            self.preferences = {}
        else:
            self.preferences = preferences
        return self.preferences

    def haveRelation(self, user):
        relation = Bot_database().getRelationByExternal(self.id, user.id)
        if relation == None:
            relation = False
        else:
            relation = True
        return relation

    def setRelation(self, userId=None, relation=None, is_favorite=False):
        self.logger.log(f'Сохраняю предпочтение пользователя {self.id} {self.name}', 'setRelation()')
        if userId == None:
            userId = Bot_database().getLastRelation(self.id)
            if userId != None:
                userId = userId['to_external']
        if userId == None:
            self.logger.log(f'Не указан кандидат, на которого реагирует пользователь. У пользователя {self.id} еще не было реакций, чтобы определить это автоматически.', 'setRelation()')
            relationId = None
        else:
            if relation:
                self.logger.log(f'Сохранение реакции пользователя {self.id} на кандидата {userId}. Реакция: лайк. Избранное: {is_favorite}', 'setRelation()')
            elif relation == None:
                self.logger.log(f'Пользователю {self.id} показали кандидата {userId}.', 'setRelation()')
            else:
                is_favorite = False
                self.logger.log(f'Сохранение реакции пользователя {self.id} на кандидата {userId}. Реакция: не нравится. Избранное: {is_favorite}', 'setRelation()')
            relationId = Bot_database().addRelation(self.id, userId, relation, is_favorite)


Bot(config.token_group)