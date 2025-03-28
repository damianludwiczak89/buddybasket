from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    username = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=50, null=True, blank=True)
    refresh_token = models.CharField(max_length=1000, null=True, blank=True)
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        email_username = self.email.split("@")[0]
        if self.username == "" or self.username == None:
            self.username = email_username
        super(User,  self).save(*args, **kwargs)

    def remove_friend(self, friend):
        if friend in self.friends.all():
            self.friends.remove(friend)
            return True
        return False

    
class Draft(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drafts')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class ShoppingList(models.Model):
    users = models.ManyToManyField(User, related_name='lists')
    name = models.CharField(max_length=100)
    draft = models.ForeignKey(Draft, on_delete=models.SET_NULL, related_name='draft', null=True, blank=True)

    def __str__(self):
        return self.name

class Item(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.SET_NULL, related_name='items', null=True, blank=True)
    draft = models.ForeignKey(Draft, on_delete=models.SET_NULL, related_name='items', null=True, blank=True)
    name = models.CharField(max_length=100)
    amount = models.IntegerField(default=1)
    bought = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class Invite(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invites")
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_invites")

    class Meta:
        unique_together = ('from_user', 'to_user')

    def accept(self):
        self.from_user.friends.add(self.to_user)
        self.delete()

    def __str__(self):
        return f"{self.from_user.username} invited {self.to_user.username}"
