import datetime
import config

class Log_manager:
    def __init__(self, source_class):
        self.file = config.file
        self.source_class = source_class

    def saveTextToFile(self, text):
        with open(self.file, 'a') as context:
            try:
                context.write('\n' + text)
            except UnicodeEncodeError as err:
                text = f'Не удалось дешифровать тест: {err}'
        return text

    def log(self, text, source=None):
        if self.source_class in config.classes.keys():
            if config.classes[self.source_class]:
                now = datetime.datetime.now()
                now = f'{now} || '
                if source != None:
                    source = f'{source} || '
                source_class = f'{self.source_class} || '
                if source == None:
                    source = ''
                text = now + source_class + source + text
                text = self.saveTextToFile(text)
                print(text)
