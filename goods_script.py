import json
import requests
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
# from .models import Product # Розкоментуй, коли створиш модель

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        try:
            update = json.loads(request.body)
            
            # Нас цікавлять повідомлення з каналів/груп
            message = update.get('message') or update.get('channel_post')
            if not message:
                return JsonResponse({"status": "ignored"})

            # Текст повідомлення (якщо з фото, то це 'caption', якщо без - 'text')
            text = message.get('caption') or message.get('text', '')
            
            # Перевіряємо, чи є фото
            if 'photo' in message:
                # Беремо фото найвищої якості (останнє в списку)
                best_photo = message['photo'][-1]
                file_id = best_photo['file_id']
                
                # Отримуємо шлях до файлу на серверах Telegram
                file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                file_info = requests.get(file_info_url).json()
                file_path = file_info['result']['file_path']
                
                # Завантажуємо сам файл
                download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                photo_response = requests.get(download_url)
                
                print("📸 Фото успішно завантажено!")
                print(f"📝 Опис до фото:\n{text}")
                print("-" * 40)

                # ТУТ ЛОГІКА ЗБЕРЕЖЕННЯ В БД:
                # product = Product(title="Назва", description=text)
                # product.image.save(f"{file_id}.jpg", ContentFile(photo_response.content), save=True)

            else:
                print(f"✉️ Звичайний текст без фото:\n{text}")

        except Exception as e:
            print(f"❌ Помилка обробки вебхука: {e}")

        # Telegram завжди очікує 200 OK, інакше спамитиме повторними запитами
        return JsonResponse({"status": "ok"})

    return JsonResponse({"error": "Method not allowed"}, status=405)