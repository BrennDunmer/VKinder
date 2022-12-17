import pathlib
#КОНФИГУРАЦИИ API ВК
token_group = ' *Токен группы* '
token_user = ' *Токен юзера* '
protocolVersion = "5.131"
vkApiUri = "https://api.vk.com/method/"
vkProd = 'https://vk.com/'
count = 20 # количество профилей в выдаче поиска, при увеличении числа до 1000 время поиска увеличивается, что неудобно для тестирования

#КОНФИГУРАЦИИ ЛОГГЕРА
file = 'log/logs.txt'
classes = {
    'Bot_database': True,
    'User_api': True,
    'Bot': True,
    'Vk_account': True
}

#КОНФИГУРАЦИИ ПОДКЛЮЧЕНИЯ К БД
dbName = ' *Имя базы данных* '
user = ' *Имя пользователя, по умолчанию postgres* '
password = ' *пароль базы данных* '
schemaName = 'public'

#СПИСОК ИСТРЕБУЕМЫХ ТАБЛИЦ
tables = [
    'account',
    'preferences',
    'users',
    'relation'
]
