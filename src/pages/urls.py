from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("story/", views.StoryView.as_view(), name="story"),
    path("contacts/", views.ContactsView.as_view(), name="contacts"),
    path("contacts/message/", views.ContactsView.as_view(), name="contacts_message"),
]
