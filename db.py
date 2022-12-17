import psycopg2
import config
from logger import Log_manager

class Bot_database:
    def __init__(self):
        self.requestToGetTables = f"select DISTINCT table_name FROM INFORMATION_SCHEMA.COLUMNS where table_schema = '{config.schemaName}'"
        self.conn = psycopg2.connect(f"dbname={config.dbName} user={config.user} password={config.password}")
        self.logger = Log_manager('Bot_database')
        self.checkTablesAndCreateIfNotExist()

    '''Отправляет запрос на сервер и возвращает ответ'''
    def sendQuery(self, request, result=True):
        try:
            cur = self.conn.cursor()
            cur.execute(request)
        except psycopg2.errors.SyntaxError as err:
            errMessage = f'Ошибка {err}\nЗапрос, который отработал с ошибкой:\n{request}'
            self.logger.log(errMessage)
        else:
            if(result):
                data = cur.fetchall()
            else:
                data = None
            self.conn.commit()
        return data

    '''Проверяет, созданы ли все таблицы в БД, и создаёт недостающие'''
    def checkTablesAndCreateIfNotExist(self):
        tables = self.sendQuery(self.requestToGetTables)
        requirimentTables = []

        for q in tables:
            for w in config.tables:
                if q[0] == w:
                    requirimentTables.append(w)
                    break

        if len(requirimentTables)<len(config.tables):
            self.logger.log('Не все искомые таблицы существуют. Начинаем создание таблиц.', 'checkTablesAndCreateIfNotExist()')
            with open('create_tables.sql') as contex:
                self.sendQuery(contex.read(), result=False)

    '''Проверяет, находится ли пользователь в бане'''
    def isBanned(self, external_id):
        query = f"select u.is_banned from account a join users u on u.account_id = a.id where a.external_id = '{external_id}'"
        data = self.sendQuery(query)
        if len(data) > 0:
            isBanned = data[0][0]
            if isBanned:
                self.logger.log(f'Пользователь {external_id} находится в бане.', 'isBanned()')
            else:
                self.logger.log(f'Пользователь {external_id} не заблокирован.', 'isBanned()')
        else:
            isBanned = None
        return isBanned

    '''Возвращает account_id и user_id для пользователя, если таковой существует'''
    def idByExternal(self, external_id):
        users = self.sendQuery(f"SELECT a.id, u.id FROM account a left join users u on u.account_id = a.id WHERE external_id = '{external_id}'")
        if (len(users) > 0):
            account_id = users[0][0]
            user_id = users[0][1]
            response = [account_id, user_id]
        else:
            response = [None, None]
        return response

    '''Добавляет пользователя и его предпочтения, если он не создан, а если уже существует - редактирует существующие предпочтения'''
    def addUser(
            self,
            external_id,
            age_from = None,
            age_to = None,
            sex_id = None,
            city_id = None,
            marital_status = None):

        id = self.idByExternal(external_id)

        if(id[0] != None):
            account_id = id[0]
        else:
            account_id = self.sendQuery(f"insert into account (external_id) values ('{external_id}') RETURNING id")[0][0]
            self.logger.log(f'Аккаунт ВК {external_id} сохранен в БД.', 'addUser()')

        result = False

        if (id[1] == None):
            values = [age_from, age_to, sex_id, city_id, marital_status]
            for q in range(len(values)):
                if(values[q] == None):
                    values[q] = 'null'
                else:
                    values[q] = f"'{str(values[q])}'"
            values = ', '.join(values)
            preference_id = self.sendQuery(f"insert into preferences (age_from, age_to, sex_id, city_id, marital_status) values ({values}) RETURNING id")[0][0]
            self.logger.log(f'Сохранены предпочтения для пользователя {external_id}.', 'addUser()')
            user_id = self.sendQuery(f"insert into users (is_banned, preferences_id, account_id) values ('false', {preference_id}, {account_id}) RETURNING id")[0][0]
            result = True
        else:
            if(self.isBanned(external_id) == False):
                preference_id = self.sendQuery(f"select p.id from account a join users u on u.account_id = a.id join preferences p on p.id = u.preferences_id where a.id = '{account_id}'")[0][0]
                if (age_from == None):
                    age_from = 'null'
                if (age_to == None):
                    age_to = 'null'
                if (sex_id == None):
                    sex_id = 'null'
                if (city_id == None):
                    city_id = 'null'
                else:
                    city_id = f"'{city_id}'"
                if (marital_status == None):
                    marital_status = 'null'
                query = f"update preferences set age_from = {age_from}, age_to = {age_to}, sex_id = {sex_id}, city_id = {city_id}, marital_status = {marital_status} where id = '{preference_id}'"
                self.sendQuery(query, result=False)
                result = True
        if result:
            self.logger.log(f'Пользователь {external_id} сохранен в БД как клиент.', 'addUser()')
        else:
            self.logger.log(f'Не удалось сохранить в БД пользователя {external_id}.', 'addUser()')
        return result

    def getPreferences(self, external_id):
        preferences = self.sendQuery(f"select p.* from account a join users u on u.account_id = a.id join preferences p on u.preferences_id = p.id where a.external_id = '{external_id}'")
        if len(preferences) > 0:
            preferences = preferences[0]
            preferences = {
                'id': preferences[0],
                'age_from': preferences[1],
                'age_to': preferences[2],
                'sex_id': preferences[3],
                'city_id': preferences[4],
                'marital_status': preferences[5]
            }
        else:
            preferences = None
        return preferences

    '''Добавляет аккаунт пользователя ВК в БД, не регистрируя его в качестве пользователя бота'''
    def addAccount(self, external_id):
        id = self.idByExternal(external_id)
        if id[0] == None:
            account_id = self.sendQuery(f"insert into account (external_id) values ('{external_id}') RETURNING id")[0][0]
            self.logger.log(f'Аккаунт ВК {external_id} сохранен в БД.', 'addAccount()')
        else:
            account_id = id[0]
        return account_id

    '''Отправляет пользователя в бан'''
    def banHammer(self, external_id):
        id = self.idByExternal(external_id)

        result = False
        if(id[1] != None):
            user_id = id[1]
            self.sendQuery(f"update users set is_banned = true where id = {user_id}", result=False)
            self.logger.log(f'Пользователь {external_id} заблокирован.', 'banHammer()')
            result = True

        return result

    '''Возвращает реакцию пользователя на кандидата'''
    def getRelationByExternal(self, from_external, to_external):
        relation_id = self.sendQuery(f"select r.id from account a join users u on u.account_id = a.id join relation r on r.user_id = u.id join account a2 on a2.id = r.account_id where a.external_id = '{from_external}' and a2.external_id = '{to_external}'")
        if len(relation_id) > 0:
            relation_id = relation_id[0][0]
        else:
            relation_id = None
        return relation_id

    '''Возвращает последнюю реакцию пользователя'''
    def getLastRelation(self, external_id):
        relation = self.sendQuery(f"select a.external_id, a2.external_id, r.id, r.reaction, r.is_favorite from account a join users u on u.account_id = a.id join relation r on r.user_id = u.id join account a2 on a2.id = r.account_id where a.external_id = '{external_id}' order by r.id desc limit 1")
        if len(relation) > 0:
            relation = relation[0]
            relation = {
                'from_external': relation[0],
                'to_external': relation[1],
                'relation_id': relation[2],
                'reaction': relation[3],
                'is_favorite': relation[4]
            }
        else:
            relation = None
        return relation

    '''Добавляет реакцию пользователя на кандидата (нравится, игнор), а если реакция существует - обновляет её'''
    def addRelation(self, from_external, to_external, reaction = None, is_favorite = False):
        fromId = self.idByExternal(from_external)
        relation_id = None

        if(fromId[1] != None and self.isBanned(from_external) == False):
            toId = self.idByExternal(to_external)
            if(toId[0] == None):
                toId[0] = self.addAccount(to_external)

            if reaction == None:
                reaction = 'null'
            else:
                reaction = str(reaction).lower()
            is_favorite = str(is_favorite).lower()

            relation_id = self.getRelationByExternal(from_external, to_external)
            if relation_id == None:
                relation_id = self.sendQuery(f"insert into relation (reaction, user_id, account_id, is_favorite) VALUES ({reaction}, '{fromId[1]}', '{toId[0]}', {is_favorite}) RETURNING id;")[0][0]
                self.logger.log(f'Добавлено предпочтение пользователя {from_external} к кандидату {to_external}', 'addRelation()')
            else:
                self.sendQuery(f"update relation set reaction = {reaction}, is_favorite = {is_favorite} where id = '{relation_id}'", result=False)
                self.logger.log(f'Обновлено предпочтение пользователя {from_external} к кандидату {to_external}', 'addRelation()')

        return relation_id

