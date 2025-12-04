"""Static test cases for retrieval coverage."""

TEST_CASES = [
    {
        "id": "tc01_fried_chicken",
        "user_input": "mình muốn ăn gà rán, càng gần cầu rồng càng tốt, giá tầm 300.000",
        "lat": 16.0650,
        "lng": 108.2290,
    },
    {
        "id": "tc02_korean_bbq",
        "user_input": "cho mình quán đồ Hàn/BBQ, khoảng 3km quanh trung tâm Hải Châu, rating trên 7, có menu nướng BBQ đa dạng",
        "lat": 16.0670,
        "lng": 108.2200,
        "want_menu": True,
    },
    {
        "id": "tc03_japanese_near_beach",
        "user_input": "tìm quán Nhật, sushi/sashimi hoặc buffet Nhật cũng được, gần biển",
        "lat": 16.0700,
        "lng": 108.2450,
    },
    {
        "id": "tc04_italian_pizza_pasta",
        "user_input": "kiếm quán Món Âu hoặc Ý, có pizza/mỳ ý, khoảng 2km",
        "lat": 16.0645,
        "lng": 108.2240,
    },
    {
        "id": "tc05_steak_western",
        "user_input": "mình muốn ăn steak bò, đồ Âu, càng gần trung tâm càng tốt, rating > 7.5",
        "lat": 16.0630,
        "lng": 108.2200,
    },
    {
        "id": "tc06_central_specialties",
        "user_input": "đặc sản Đà Nẵng/miền Trung, kiểu bánh tráng thịt heo, phạm vi 3km",
        "lat": 16.0700,
        "lng": 108.2200,
        "distance_limit_km": 3.0,
    },
    {
        "id": "tc07_vietnamese_thanh_khe",
        "user_input": "cần quán Việt Nam, cơm gà hoặc món Việt, khu Thanh Khê",
        "lat": 16.0700,
        "lng": 108.2100,
    },
    {
        "id": "tc08_buffet_korean_japanese",
        "user_input": "buffet nướng kiểu Nhật/Hàn, mình ở gần Lê Duẩn",
        "lat": 16.0690,
        "lng": 108.2100,
    },
    {
        "id": "tc09_fastfood_chicken_burger",
        "user_input": "muốn ăn gà rán/burger kiểu fastfood, gần chợ Hàn (Hải Châu)",
        "lat": 16.0668,
        "lng": 108.2250,
    },
    {
        "id": "tc10_asian_mix_vincom",
        "user_input": "tìm quán Á tổng hợp (Món Á), miễn là rating ổn, trong bán kính 2km từ Vincom",
        "lat": 16.0716,
        "lng": 108.2307,
        "distance_limit_km": 2.0,
    },
]
