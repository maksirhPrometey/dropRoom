# DropRoom — Database Schema

**Stack:** Django 5+ · Python 3.12+ · PostgreSQL  
**Apps:** 5 · **Models:** 30 · **Структура:** `src/<app>/models.py`

---

## Зміст

- [catalog](#catalog) — бренди, категорії, дропи, товари
- [accounts](#accounts) — користувачі, адреси, вішліст
- [orders](#orders) — кошик, замовлення, промокоди
- [marketing](#marketing) — розсилка, нагадування
- [pages](#pages) — CMS-контент кожної сторінки

---

## `catalog`

> Каталог товарів. Центральний app. Всі продуктові сутності живуть тут.

### `Brand`

Бренд-партнер магазину (Acne Studios, Nike, Tom Ford тощо).

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `name` | `CharField(100)` | unique |
| `slug` | `SlugField(100)` | unique |
| `country` | `CharField(80)` | blank |
| `logo` | `ImageField` | null, blank |
| `is_active` | `BooleanField` | default `True` |

---

### `Category`

Ієрархічна категорія товарів (Sneakers, Outerwear, Knitwear…). Підтримує одного батька — дворівнева структура (категорія / підкатегорія).

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `name` | `CharField(100)` | — |
| `slug` | `SlugField(100)` | unique |
| `parent` | `ForeignKey('self')` | null, blank, `SET_NULL` |
| `sort_order` | `PositiveSmallIntegerField` | default `0` |
| `is_featured` | `BooleanField` | default `False` |

---

### `Color`

Довідник кольорів для варіантів товару. Окремо від варіанта — щоб фільтр в каталозі брав значення звідси.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `name` | `CharField(80)` | — |
| `slug` | `SlugField` | unique |
| `hex_code` | `CharField(7)` | формат `#rrggbb` |

---

### `Drop`

Дроп — пронумерований двотижневий реліз колекції. Центральна бізнес-сутність магазину.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `number` | `PositiveSmallIntegerField` | unique (047, 048…) |
| `title` | `CharField(200)` | — |
| `theme` | `CharField(200)` | blank |
| `season` | `CharField(10)` | `S/S` або `F/W` |
| `year` | `PositiveSmallIntegerField` | — |
| `scheduled_at` | `DateTimeField` | дата і час релізу |
| `is_live` | `BooleanField` | default `False` |
| `cover_image` | `ImageField` | null, blank |

---

### `Product`

Товар у каталозі. Прив'язаний до бренду, категорії та (опційно) дропу. Сам по собі не має ціни — ціна на рівні `ProductVariant`.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `brand` | `ForeignKey(Brand)` | `PROTECT` |
| `category` | `ForeignKey(Category)` | `PROTECT` |
| `drop` | `ForeignKey(Drop)` | null, blank, `SET_NULL` |
| `name` | `CharField(255)` | — |
| `slug` | `SlugField` | unique |
| `subtitle` | `CharField(255)` | blank (напр. *Charcoal · oversized*) |
| `description` | `TextField` | blank |
| `gender` | `CharField(10)` | choices: `W` / `M` / `U` |
| `material` | `CharField(255)` | blank |
| `base_price` | `DecimalField(10,2)` | — |
| `is_active` | `BooleanField` | default `True` |
| `created_at` | `DateTimeField` | `auto_now_add` |

---

### `ProductVariant`

Конкретна одиниця товару: розмір + колір + залишок + SKU. Саме цей запис потрапляє в кошик і замовлення.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `product` | `ForeignKey(Product)` | `CASCADE` |
| `color` | `ForeignKey(Color)` | null, `SET_NULL` |
| `size` | `CharField(20)` | XS/S/M/L або 36/38… |
| `sku` | `CharField(64)` | unique |
| `price` | `DecimalField(10,2)` | може відрізнятись від `base_price` |
| `stock_qty` | `PositiveIntegerField` | default `0` |
| `is_available` | `BooleanField` | default `True` |

---

### `ProductImage`

Зображення товару. Підтримує кілька зображень на товар з позначкою основного.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `product` | `ForeignKey(Product)` | `CASCADE` |
| `image` | `ImageField` | — |
| `alt` | `CharField(255)` | blank |
| `is_primary` | `BooleanField` | default `False` |
| `sort_order` | `PositiveSmallIntegerField` | default `0` |

---

## `accounts`

> Розширення стандартного Django `User`. Адреси, вішліст, профіль.

### `UserProfile`

Розширення вбудованого `User` через `OneToOneField`. Зберігає дані специфічні для DropRoom.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `OneToOneField(User)` | `CASCADE` |
| `phone` | `CharField(20)` | blank |
| `city` | `CharField(100)` | blank |
| `newsletter_opt_in` | `BooleanField` | default `False` |
| `created_at` | `DateTimeField` | `auto_now_add` |

---

### `Address`

Адреса доставки. Користувач може мати кілька адрес, одна — основна.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `ForeignKey(User)` | `CASCADE` |
| `label` | `CharField(100)` | blank (напр. *Дім*, *Офіс*) |
| `full_name` | `CharField(255)` | — |
| `phone` | `CharField(20)` | — |
| `city` | `CharField(100)` | — |
| `street` | `CharField(255)` | — |
| `building` | `CharField(20)` | — |
| `flat` | `CharField(20)` | blank |
| `np_warehouse` | `CharField(255)` | blank (відділення Нової Пошти) |
| `is_default` | `BooleanField` | default `False` |

---

### `WishlistItem`

Елемент вішлісту — «Зберегти на потім». Прив'язаний до конкретного варіанта (розмір + колір).  
`unique_together: (user, variant)`

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `ForeignKey(User)` | `CASCADE` |
| `variant` | `ForeignKey(ProductVariant)` | `CASCADE` |
| `added_at` | `DateTimeField` | `auto_now_add` |

---

## `orders`

> Промокоди, кошики, замовлення. Вся комерційна логіка.

### `PromoCode`

Промокод зі знижкою у відсотках або фіксованій сумі. Може бути обмежений одним брендом.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `code` | `CharField(50)` | unique |
| `discount_type` | `CharField(10)` | choices: `PERCENT` / `FIXED` |
| `discount_value` | `DecimalField(8,2)` | — |
| `brand` | `ForeignKey(Brand)` | null, blank, `SET_NULL` |
| `min_order` | `DecimalField(10,2)` | default `0` |
| `max_uses` | `PositiveIntegerField` | null = без ліміту |
| `uses_count` | `PositiveIntegerField` | default `0` |
| `valid_from` | `DateTimeField` | — |
| `valid_until` | `DateTimeField` | — |
| `is_active` | `BooleanField` | default `True` |

---

### `Cart`

Кошик. Працює і для анонімів (через `session_key`), і для авторизованих. При логіні — мердж анонімного кошика з користувацьким.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `ForeignKey(User)` | null, blank, `SET_NULL` |
| `session_key` | `CharField(64)` | blank (для анонімів) |
| `promo` | `ForeignKey(PromoCode)` | null, blank, `SET_NULL` |
| `created_at` | `DateTimeField` | `auto_now_add` |
| `updated_at` | `DateTimeField` | `auto_now` |

---

### `CartItem`

Позиція в кошику. Один запис = один варіант товару з кількістю.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `cart` | `ForeignKey(Cart)` | `CASCADE` |
| `variant` | `ForeignKey(ProductVariant)` | `CASCADE` |
| `quantity` | `PositiveSmallIntegerField` | default `1` |
| `added_at` | `DateTimeField` | `auto_now_add` |

---

### `Order`

Оформлене замовлення. Статус переходить від `PENDING` до `DONE` або `CANCELLED`. Після оформлення прив'язані `OrderItem` зберігають знімок цін.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `ForeignKey(User)` | null, `SET_NULL` |
| `address` | `ForeignKey(Address)` | null, `SET_NULL` |
| `promo` | `ForeignKey(PromoCode)` | null, `SET_NULL` |
| `status` | `CharField(20)` | `PENDING` / `PAID` / `SHIPPED` / `DONE` / `CANCELLED` |
| `payment_method` | `CharField(20)` | `CARD` / `APPLE_PAY` / `GPAY` / `CASH` |
| `subtotal` | `DecimalField(10,2)` | — |
| `discount_amount` | `DecimalField(10,2)` | default `0` |
| `delivery_cost` | `DecimalField(10,2)` | default `0` |
| `total` | `DecimalField(10,2)` | — |
| `notes` | `TextField` | blank |
| `created_at` | `DateTimeField` | `auto_now_add` |
| `updated_at` | `DateTimeField` | `auto_now` |

---

### `OrderItem`

Рядок замовлення. Зберігає **знімок** назви, бренду і ціни на момент покупки — щоб зміна каталогу не впливала на архів замовлень.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `order` | `ForeignKey(Order)` | `CASCADE` |
| `variant` | `ForeignKey(ProductVariant)` | null, `SET_NULL` |
| `name_snapshot` | `CharField(255)` | знімок назви |
| `brand_snapshot` | `CharField(100)` | знімок бренду |
| `price_snapshot` | `DecimalField(10,2)` | знімок ціни |
| `quantity` | `PositiveSmallIntegerField` | — |

---

## `marketing`

> Email-розсилка і нагадування про дропи.

### `NewsletterSubscriber`

Підписник email-розсилки. Не обов'язково є зареєстрованим користувачем.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `email` | `EmailField` | unique |
| `is_active` | `BooleanField` | default `True` |
| `created_at` | `DateTimeField` | `auto_now_add` |

---

### `DropNotification`

Запит на нагадування про конкретний дроп. Надсилається за 24 години до `Drop.scheduled_at`.

| Поле | Тип Django | Обмеження |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `drop` | `ForeignKey(Drop)` | `CASCADE` |
| `email` | `EmailField` | — |
| `user` | `ForeignKey(User)` | null, blank, `SET_NULL` |
| `created_at` | `DateTimeField` | `auto_now_add` |

---

## `pages`

> CMS-контент кожної сторінки сайту. Singleton-моделі редагуються через django-admin, списки — через `TabularInline`.  
> **Singleton** = завжди один запис, `pk=1`. `save()` перевизначено — забороняє створення другого.

### `SiteSettings` *(singleton)*

Глобальні налаштування магазину, доступні на всіх сторінках.

| Поле | Тип Django | Значення за замовч. |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `free_delivery_threshold` | `DecimalField(10,2)` | `3000` |
| `return_period_days` | `PositiveSmallIntegerField` | `14` |
| `pickup_reserve_hours` | `PositiveSmallIntegerField` | `24` |
| `support_hours` | `CharField(100)` | *09:00 — 23:00, щодня* |
| `response_time_mins` | `PositiveSmallIntegerField` | `4` |
| `telegram_support` | `CharField(50)` | *@droproom_support* |
| `telegram_channel` | `CharField(50)` | *@droproom_drops* |
| `phone_main` | `CharField(20)` | — |
| `email_main` | `EmailField` | *hello@droproom.ua* |
| `email_press` | `EmailField` | *press@droproom.ua* |
| `instagram_url` | `URLField` | — |
| `founded_year` | `PositiveSmallIntegerField` | `2019` |
| `footer_desc` | `CharField(255)` | рядок під лого у футері |

---

### `UtilityBarItem`

Рядки анонсів у marquee-стрічці зверху сторінки. Виводяться всі `is_active=True`, відсортовані за `sort_order`.

| Поле | Тип Django | Примітки |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `text` | `CharField(200)` | напр. *Безкоштовна доставка від 3 000 ₴* |
| `sort_order` | `PositiveSmallIntegerField` | — |
| `is_active` | `BooleanField` | default `True` |

---

### `HomePage` *(singleton)*

Контент головної сторінки — секції hero, editorial, newsletter.

| Поле | Тип Django | Де виводиться |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `hero_blurb` | `TextField` | абзац під великим заголовком |
| `editorial_stamp` | `CharField(100)` | плашка на фото (*Studio shoot · 047*) |
| `editorial_image` | `ImageField` | null — фото editorial-секції |
| `editorial_eyebrow` | `CharField(100)` | надзаголовок (*— Drop Story*) |
| `editorial_title_main` | `CharField(100)` | рядок заголовка |
| `editorial_title_accent` | `CharField(100)` | italic-рядок в акцентному кольорі |
| `editorial_body_1` | `TextField` | перший абзац editorial |
| `editorial_body_2` | `TextField` | другий абзац editorial |
| `newsletter_heading_1` | `CharField(100)` | рядок 1 заголовка розсилки |
| `newsletter_heading_2` | `CharField(100)` | рядок 2 (italic) |
| `newsletter_heading_3` | `CharField(100)` | рядок 3 |
| `newsletter_subtext` | `TextField` | підпис під формою |
| `newsletter_counter_label` | `CharField(60)` | *26 482 підписники · 0% спаму* |

---

### `StatBlock`

Чотири числових блоки у стрічці статистики на головній (`FK → HomePage`).

| Поле | Тип Django | Приклад |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(HomePage)` | `CASCADE` |
| `label` | `CharField(100)` | *Брендів-партнерів* |
| `value` | `CharField(50)` | *25* |
| `description` | `CharField(255)` | *Прямі контракти, без перекупників.* |
| `sort_order` | `PositiveSmallIntegerField` | — |

---

### `CatalogPage` *(singleton)*

Hero-секція каталогу та SEO-мета.

| Поле | Тип Django | Примітки |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `hero_title_main` | `CharField(200)` | *Всі бренди /* |
| `hero_title_accent` | `CharField(200)` | *всі дропи* |
| `hero_blurb` | `TextField` | підзаголовок-абзац |
| `seo_title` | `CharField(200)` | blank |
| `seo_description` | `TextField` | blank |

---

### `StoryPage` *(singleton)*

Контент сторінки «Про нас» — все крім динамічних секцій (pillars, timeline, team — окремі моделі нижче).

| Поле | Тип Django | Де виводиться |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `hero_title_1` | `CharField(100)` | *One room.* |
| `hero_title_2` | `CharField(100)` | *Twenty-five* |
| `hero_title_accent` | `CharField(100)` | *brands.* (accent-колір) |
| `hero_lead` | `TextField` | головний абзац hero |
| `pillars_heading` | `CharField(200)` | заголовок секції принципів |
| `timeline_heading_main` | `CharField(100)` | *Як ми* |
| `timeline_heading_2` | `CharField(100)` | *сюди* |
| `timeline_heading_accent` | `CharField(100)` | *прийшли* |
| `timeline_intro` | `TextField` | абзац під заголовком хронології |
| `quote_text` | `TextField` | цитата засновників |
| `quote_author` | `CharField(200)` | *— Олександра Кравець & Антон Мельник* |
| `cta_heading_1` | `CharField(100)` | *Заходь* |
| `cta_heading_2` | `CharField(200)` | *у DropRoom* |

---

### `StoryPillar`

Три принципи роботи магазину (`FK → StoryPage`). Керуються через `TabularInline` в адмінці.

| Поле | Тип Django | Приклад |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(StoryPage)` | `CASCADE` |
| `number` | `PositiveSmallIntegerField` | `1` / `2` / `3` |
| `title_line1` | `CharField(100)` | *Прямі* |
| `title_line2` | `CharField(100)` | *контракти* |
| `body` | `TextField` | абзац принципу |
| `sort_order` | `PositiveSmallIntegerField` | — |

---

### `StoryTimelineEvent`

Хронологія розвитку магазину (`FK → StoryPage`).

| Поле | Тип Django | Примітки |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(StoryPage)` | `CASCADE` |
| `year` | `CharField(10)` | *2019*, *2026* |
| `is_accent_year` | `BooleanField` | `True` → рік в акцентному кольорі |
| `heading` | `CharField(200)` | *Перша студія на Подолі* |
| `body` | `TextField` | опис події |
| `drop_tag` | `CharField(50)` | *— Drop 001* |
| `sort_order` | `PositiveSmallIntegerField` | — |

---

### `TeamMember`

Члени команди (`FK → StoryPage`).

| Поле | Тип Django | Примітки |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(StoryPage)` | `CASCADE` |
| `name` | `CharField(200)` | *Олександра Кравець* |
| `role` | `CharField(200)` | *Co-founder · Buying* |
| `bio` | `TextField` | — |
| `photo` | `ImageField` | null |
| `sort_order` | `PositiveSmallIntegerField` | — |
| `is_active` | `BooleanField` | default `True` |

---

### `ContactsPage` *(singleton)*

Статичний контент сторінки контактів (Hero, вступ до форми, FAQ-заголовок). Бутіки, канали і FAQ — окремі моделі нижче.

| Поле | Тип Django | Де виводиться |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `hero_lead` | `TextField` | абзац під h1 |
| `channels_desc` | `TextField` | вступ до секції каналів |
| `form_heading_1` | `CharField(100)` | *Напиши* |
| `form_heading_2` | `CharField(100)` | *нам /* |
| `form_heading_accent` | `CharField(100)` | *не форма* |
| `form_aside_body` | `TextField` | пояснювальний текст ліворуч від форми |
| `faq_heading_main` | `CharField(100)` | *Часті /* |
| `faq_heading_accent` | `CharField(100)` | *питання* |
| `faq_intro` | `TextField` | підпис під заголовком FAQ |

---

### `Store`

Бутік (`FK → ContactsPage`). Три записи: Київ, Львів, Дніпро.

| Поле | Тип Django | Приклад |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(ContactsPage)` | `CASCADE` |
| `city` | `CharField(100)` | *Київ* |
| `label` | `CharField(50)` | *Flagship* / *Boutique* / *New* |
| `address` | `CharField(255)` | *вул. Хрещатик 22, 2-й поверх* |
| `hours` | `CharField(100)` | *Щодня 11:00 — 22:00* |
| `phone` | `CharField(20)` | — |
| `telegram` | `CharField(50)` | *@droproom_kyiv* |
| `pickup_eta` | `CharField(50)` | *за 2 год* |
| `maps_url` | `URLField` | null — посилання на Google Maps |
| `lat` | `DecimalField(9,6)` | null |
| `lng` | `DecimalField(9,6)` | null |
| `sort_order` | `PositiveSmallIntegerField` | — |
| `is_active` | `BooleanField` | default `True` |

---

### `ContactChannel`

Канал зв'язку (`FK → ContactsPage`). Чотири записи: Telegram, телефон, email, преса.

| Поле | Тип Django | Приклад |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(ContactsPage)` | `CASCADE` |
| `label` | `CharField(50)` | *— No. 01 · найшвидше* |
| `value` | `CharField(100)` | *@droproom_support* |
| `meta` | `CharField(200)` | *Telegram · відповідаємо за 4 хв* |
| `url` | `CharField(200)` | *https://t.me/droproom_support* |
| `sort_order` | `PositiveSmallIntegerField` | — |
| `is_active` | `BooleanField` | default `True` |

---

### `FAQItem`

Питання-відповідь в акордеоні (`FK → ContactsPage`).

| Поле | Тип Django | Примітки |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `page` | `ForeignKey(ContactsPage)` | `CASCADE` |
| `question` | `CharField(255)` | — |
| `answer` | `TextField` | — |
| `sort_order` | `PositiveSmallIntegerField` | — |
| `is_active` | `BooleanField` | default `True` |

---

## Зв'язки між моделями

```
catalog
  Category ──self──▶ Category (parent)
  Brand ──────────▶ Product
  Category ───────▶ Product
  Drop ────────────▶ Product
  Product ─────────▶ ProductVariant
  Color ───────────▶ ProductVariant
  Product ─────────▶ ProductImage

accounts
  User ────1:1────▶ UserProfile
  User ────────────▶ Address
  User ────────────▶ WishlistItem ◀──── ProductVariant

orders
  Brand ───────────▶ PromoCode
  User ────────────▶ Cart
  PromoCode ───────▶ Cart
  Cart ────────────▶ CartItem ◀──────── ProductVariant
  User ────────────▶ Order
  Address ─────────▶ Order
  PromoCode ───────▶ Order
  Order ───────────▶ OrderItem ◀─────── ProductVariant

marketing
  Drop ────────────▶ DropNotification
  User ────────────▶ DropNotification

pages
  HomePage ────────▶ StatBlock
  StoryPage ───────▶ StoryPillar
  StoryPage ───────▶ StoryTimelineEvent
  StoryPage ───────▶ TeamMember
  ContactsPage ────▶ Store
  ContactsPage ────▶ ContactChannel
  ContactsPage ────▶ FAQItem
```

---

## Структура проекту

```
src/
├── catalog/
│   └── models.py     Brand · Category · Color · Drop · Product · ProductVariant · ProductImage
├── accounts/
│   └── models.py     UserProfile · Address · WishlistItem
├── orders/
│   └── models.py     PromoCode · Cart · CartItem · Order · OrderItem
├── marketing/
│   └── models.py     NewsletterSubscriber · DropNotification
└── pages/
    └── models.py     SiteSettings · UtilityBarItem · HomePage · StatBlock
                      CatalogPage · StoryPage · StoryPillar · StoryTimelineEvent · TeamMember
                      ContactsPage · Store · ContactChannel · FAQItem
```

---

*Сформовано на базі верстки DropRoom · травень 2026*
