"""Генератор эталонного корпуса для бенчмарка (Спринт 10.0)."""
import json
from pathlib import Path
from docx import Document

CORPUS_DIR = Path("benchmark/corpus")
GT_FILE = Path("benchmark/ground_truth.json")

CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Эталонные данные
docs_data = {
    "01_dogovor_postavki.docx": {
        "text": [
            "ДОГОВОР ПОСТАВКИ № 123/2024",
            "г. Москва, 15.05.2024",
            "Общество с ограниченной ответственностью «Ромашка», ИНН 7707083893, КПП 770701001,",
            "в лице генерального директора Петрова Петра Петровича,",
            "действующего на основании Устава, именуемое в дальнейшем «Поставщик»,",
            "и Индивидуальный предприниматель Сидоров Иван Иванович, ИНН 502409876543,",
            "адрес: 141000, Московская обл., г. Мытищи, ул. Ленина, д. 10, кв. 5,",
            "телефон: +7 (900) 123-45-67, email: ivan.sidorov@example.com,",
            "именуемый в дальнейшем «Покупатель», заключили настоящий договор о нижеследующем:"
        ],
        "entities": [
            {"category": "COMPANY", "value": "Ромашка"},
            {"category": "INN", "value": "7707083893"},
            {"category": "KPP", "value": "770701001"},
            {"category": "PERSON", "value": "Петрова Петра Петровича"},
            {"category": "PERSON", "value": "Сидоров Иван Иванович"},
            {"category": "INN", "value": "502409876543"},
            {"category": "ADDRESS", "value": "141000, Московская обл., г. Мытищи, ул. Ленина, д. 10, кв. 5"},
            {"category": "PHONE", "value": "+7 (900) 123-45-67"},
            {"category": "EMAIL", "value": "ivan.sidorov@example.com"}
        ]
    },
    "02_sudebny_akt.docx": {
        "text": [
            "РЕШЕНИЕ ИМЕНЕМ РОССИЙСКОЙ ФЕДЕРАЦИИ",
            "10 октября 2024 года, Ленинский районный суд г. Екатеринбурга",
            "Судья Иванов И.И., рассмотрев в открытом судебном заседании дело № 2-1234/2024",
            "по иску Смирновой Анны Владимировны к ООО «ТехноСтрой»",
            "о взыскании задолженности в размере 150 000 рублей,",
            "установил: Исковые требования удовлетворить частично.",
            "Паспортные данные истца: 45 00 123456, выдан 01.01.2010.",
            "СНИЛС: 123-456-789 01."
        ],
        "entities": [
            {"category": "PERSON", "value": "Иванов И.И."},
            {"category": "PERSON", "value": "Смирновой Анны Владимировны"},
            {"category": "COMPANY", "value": "ТехноСтрой"},
            {"category": "AMOUNT", "value": "150 000"},
            {"category": "PASSPORT", "value": "45 00 123456"},
            {"category": "DATE", "value": "01.01.2010"},
            {"category": "SNILS", "value": "123-456-789 01"}
        ]
    },
    "03_kadrovyy_prikaz.docx": {
        "text": [
            "ПРИКАЗ № 45-К",
            "О приеме на работу",
            "Принять на работу с 01.11.2024 Кузнецова Дмитрия Сергеевича",
            "на должность главного инженера.",
            "Оклад: 120 000 рублей.",
            "Основание: паспорт серии 46 05 № 987654, выдан УФМС по г. Москве.",
            "СНИЛС: 987-654-321 00, ИНН: 771234567890.",
            "Генеральный директор: Морозов А.А."
        ],
        "entities": [
            {"category": "DATE", "value": "01.11.2024"},
            {"category": "PERSON", "value": "Кузнецова Дмитрия Сергеевича"},
            {"category": "AMOUNT", "value": "120 000"},
            {"category": "PASSPORT", "value": "46 05 № 987654"},
            {"category": "SNILS", "value": "987-654-321 00"},
            {"category": "INN", "value": "771234567890"},
            {"category": "PERSON", "value": "Морозов А.А."}
        ]
    },
    "04_meditsinskaya_karta.docx": {
        "text": [
            "Амбулаторная карта № 789",
            "Пациент: Волкова Елена Игоревна, 12.05.1985 г.р.",
            "Полис ОМС: 1234567890123456",
            "Диагноз: J06.9 Острая инфекция верхних дыхательных путей.",
            "Адрес регистрации: г. Санкт-Петербург, Невский пр., д. 100, кв. 15.",
            "Телефон для связи: 8 (812) 555-44-33."
        ],
        "entities": [
            {"category": "PERSON", "value": "Волкова Елена Игоревна"},
            {"category": "DATE", "value": "12.05.1985"},
            {"category": "POLIS_OMS", "value": "1234567890123456"},
            {"category": "DIAGNOSIS", "value": "J06.9 Острая инфекция верхних дыхательных путей"},
            {"category": "ADDRESS", "value": "г. Санкт-Петербург, Невский пр., д. 100, кв. 15"},
            {"category": "PHONE", "value": "8 (812) 555-44-33"}
        ]
    },
    "05_tendernaya_dokumentatsiya.docx": {
        "text": [
            "ПРОТОКОЛ рассмотрения заявок на участие в электронном аукционе № 0373200015524000001",
            "Заказчик: ГБУЗ «Городская больница № 1»",
            "Участник 1: ООО «МедТехСервис», ИНН 7701234567, КПП 770101001.",
            "Контактное лицо: Николаев Петр Иванович, тел. +79161112233.",
            "Предложенная цена: 1 500 000.00 рублей."
        ],
        "entities": [
            {"category": "COMPANY", "value": "ГБУЗ «Городская больница № 1»"},
            {"category": "COMPANY", "value": "МедТехСервис"},
            {"category": "INN", "value": "7701234567"},
            {"category": "KPP", "value": "770101001"},
            {"category": "PERSON", "value": "Николаев Петр Иванович"},
            {"category": "PHONE", "value": "+79161112233"},
            {"category": "AMOUNT", "value": "1 500 000.00"}
        ]
    }
}

ground_truth = {}

for filename, data in docs_data.items():
    doc = Document()
    for line in data["text"]:
        doc.add_paragraph(line)
    
    filepath = CORPUS_DIR / filename
    doc.save(filepath)
    print(f"✅ Создан: {filename}")
    
    ground_truth[filename] = data["entities"]

with open(GT_FILE, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, ensure_ascii=False, indent=2)

print(f"✅ Эталонный корпус готов: {len(docs_data)} документов.")
print(f"✅ Файл разметки: {GT_FILE}")