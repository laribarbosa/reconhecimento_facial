from tortoise import fields, models
from tortoise.models import Model

class User(models.Model):
    id = fields.IntField(pk=True)
    nome = fields.CharField(max_length=100)
    nivel_seguranca = fields.IntField()  # 1, 2 ou 3
    division = fields.CharField(max_length=50, null=True)
    image_path = fields.CharField(max_length=255)

class Log(models.Model):
    id = fields.IntField(pk=True)
    nome = fields.CharField(max_length=100, null=True)
    nivel_seguranca = fields.IntField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
    acesso = fields.BooleanField()
    msg = fields.CharField(max_length=255, null=True)

    def __str__(self):
        return f'{self.timestamp} {self.nome} ({self.acesso})'
