from django.shortcuts import render, get_object_or_404
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode 
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import Http404

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed

from . import serializer as api_serializer
from .models import User, ShoppingList, Item, Draft
import random


from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()

class MyTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        user = User.objects.filter(email=email).first()

        # Custom message on a wrong password because on default it returned 'no active account' msg
        if user:
            if not user.check_password(password):
                raise AuthenticationFailed("Incorrect password")

        return super().post(request, *args, **kwargs)



class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = api_serializer.RegisterSerializer


def generate_random_otp(length=7):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


class PasswordResetEmailVerifyAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = api_serializer.UserSerializer

    def get(self, request, email):
        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        uuidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        refresh = RefreshToken.for_user(user)
        refresh_token = str(refresh.access_token)
        user.refresh_token = refresh_token
        user.otp = generate_random_otp()
        user.save()

        link = f"http://localhost:8000/api/user/reset-password/?otp={user.otp}&uuidb64={uuidb64}&=refresh_token={refresh_token}"
        
        email_data = {
            "link": link,
            "username": user.username
        }

        subject = "Password Reset Email"
        text_body = render_to_string("email/password_reset.txt", email_data)
        html_body = render_to_string("email/password_reset.html", email_data)

        msg = EmailMultiAlternatives(
            subject=subject,
            from_email=settings.FROM_EMAIL,
            to=[user.email],
            body=text_body
        )

        msg.attach_alternative(html_body, "text/html")
        msg.send()

        return Response({"message": "Password reset email sent successfully"}, status=status.HTTP_200_OK)
    

class PasswordChangeAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = api_serializer.UserSerializer

    def get(self, request, *args, **kwargs):
        otp = request.GET.get('otp')
        uuidb64 = request.GET.get('uuidb64')
        if not otp or not uuidb64:
            return Response({"message": "Invalid or inactive link"}, status=status.HTTP_400_BAD_REQUEST)

        decoded_uuidb64 = int(force_str(urlsafe_base64_decode(uuidb64)))
        user = User.objects.filter(id=decoded_uuidb64, otp=otp).first()
        
        if not user or user.otp != otp:
            return Response({"message": "Invalid or inactive link"}, status=status.HTTP_400_BAD_REQUEST)
        
        return render(request, 'buddybasket/password_reset_form.html', {'otp': otp, 'uuidb64': uuidb64})

    def post(self, request, *args, **kwargs):
        otp = request.data['otp']
        uuidb64 = request.data['uuidb64']
        password = request.data['password']
        confirm_password = request.data['confirm_password']

        decoded_uuidb64 = int(force_str(urlsafe_base64_decode(uuidb64)))
        user = User.objects.filter(id=decoded_uuidb64, otp=otp).first()

        if not user:
            return Response({"message": "User does not exist"}, status = status.HTTP_404_NOT_FOUND)
        if password != confirm_password:
            return Response({"message": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password, user)
        except ValidationError as err:
            return Response({"message": err.messages}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.otp = ""
        user.save()

        return Response({"message": "Password Changed Successfully"}, status = status.HTTP_200_OK)


class ShoppingListAPIView(APIView):
    serializer_class = api_serializer.ShoppingListSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None, *args, **kwargs):

        if id:
            shopping_list = get_object_or_404(ShoppingList.objects.prefetch_related('items'), id=id)
            serializer = self.serializer_class(shopping_list)
            return Response(serializer.data)

        queryset = ShoppingList.objects.filter(users=request.user).prefetch_related('items')
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    def delete(self, request, id, *args, **kwargs):
        shopping_list = get_object_or_404(ShoppingList, id=id)
        shopping_list.delete()
        return Response({"message": "Shopping list deleted successfully"}, status=status.HTTP_202_ACCEPTED) 

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            items_data = serializer.validated_data.pop('items', []) # in case of not providing items at all
            shopping_list = ShoppingList.objects.create(**serializer.validated_data)
            shopping_list.users.add(request.user)

            for item_data in items_data:
                Item.objects.create(shopping_list=shopping_list, **item_data)

            return Response({"message": "Shopping list addedd successfully"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, id, *args, **kwargs):
        shopping_list = get_object_or_404(ShoppingList.objects.prefetch_related('items'), id=id)
        serializer = self.serializer_class(shopping_list).data
        new_data = self.serializer_class(data=request.data)
        if new_data.is_valid():
            # unattach old items from the shopping list
            for item in serializer['items']:
                old_item = Item.objects.get(id=item['id'])
                old_item.shopping_list = None
                if old_item.draft or old_item.shopping_list:
                    old_item.save()
                else:
                    old_item.delete()

            # Create new items and relate them to the shopping list
            new_data = new_data.validated_data
            for item in new_data['items']:
                new_item = Item(name=item['name'], amount=item['amount'], bought=item['bought'], shopping_list=shopping_list)
                new_item.save()

        return Response({"message": "Shopping list changed successfully"}, status=status.HTTP_202_ACCEPTED) 


class DraftAPIView(APIView):
    serializer_class = api_serializer.DraftSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None, *args, **kwargs):
        if id:
            draft = get_object_or_404(Draft.objects.prefetch_related('items'), id=id, user=request.user).prefetch_related('items')
            serializer = self.serializer_class(draft)
            return Response(serializer.data)
        
        queryset = Draft.objects.filter(user=request.user).prefetch_related('items')
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    def delete(self, request, id, *args, **kwargs):
        draft = get_object_or_404(Draft, id=id)
        draft.delete()
        return Response({"message": "Draft list deleted successfully"}, status=status.HTTP_202_ACCEPTED) 

    def post(self, request, *args, **kwargs):
        print('post')
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            items_data = serializer.validated_data.pop('items', []) # in case of not providing items at all
            draft = Draft.objects.create(**serializer.validated_data, user=request.user)

            # create also a shopping list with same data if checkbox active was also checked
            active = request.data.get('activeAndDraft', False)
            if active:
                shopping_list = ShoppingList.objects.create(**serializer.validated_data, draft=draft)
                shopping_list.users.add(request.user)
            for item_data in items_data:
                if active:
                    Item.objects.create(draft=draft, shopping_list = shopping_list, **item_data)
                else:
                    Item.objects.create(draft=draft, **item_data)

            return Response({"message": "Draft addedd successfully"}, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, id, *args, **kwargs):
        draft = get_object_or_404(Draft.objects.prefetch_related('items'), id=id, user=request.user)
        serializer = self.serializer_class(draft).data

        # Create a shopping list from a draft (activate)
        if request.data.get('activate'):
            new_shopping_list = ShoppingList.objects.create(name=serializer.get('name'), draft=draft)
            new_shopping_list.users.add(request.user)


            items = [int(x['id']) for x in serializer.get('items')]
            items = Item.objects.filter(id__in=items)
            for item in items:
                # Creating new Item instead of adding shoppinglist to existing Item, in case of activating 1 draft multiple times
                new_item = Item(name=item.name, amount=item.amount, shopping_list=new_shopping_list)
                new_item.save()
                return Response({"message": "Draft addedd successfully"}, status=status.HTTP_201_CREATED)
        # Edit draft
        else:
            print(serializer)
            new_data = self.serializer_class(data=request.data)
            if new_data.is_valid():
                # Unattach old items from draft
                for item in serializer['items']:
                    old_item = Item.objects.get(id=item['id'])
                    old_item.draft = None
                    if old_item.draft or old_item.shopping_list:
                        old_item.save()
                    else:
                        old_item.delete()
                        

                # Create new items and relate them to the draft
                new_data = new_data.validated_data
                for item in new_data['items']:
                    new_item = Item(name=item['name'], amount=item['amount'], bought=item['bought'], draft=draft)
                    new_item.save()

            return Response({"message": "Draft edited successfully"}, status=status.HTTP_201_CREATED)

        
    
class ItemAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = api_serializer.ItemSerializer

    def put(self, request, id, *args, **kwargs):
        item = get_object_or_404(Item, id=id)
        bought = request.data.get('bought')
        item.bought = bought
        item.save()
        serializer = self.serializer_class(item)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FriendsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = api_serializer.UserSerializer

    def get(self, request, *args, **kwargs):
        queryset = User.objects.filter(friends=request.user)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request, *args, **kwargs):
        user = User.objects.get(pk=request.user.id)

        # TODO - check if user already is a friend

        new_friend = request.data["friends"]
        user.friends.add(new_friend)
        return Response({"message": "New friend added successfully"}, status=status.HTTP_200_OK)
    

class UserSearchAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        email = self.kwargs.get('email', None)
        if email:
            return User.objects.get(email=email)
        raise Http404 