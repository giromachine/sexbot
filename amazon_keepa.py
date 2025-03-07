import keepa

ASIN = 'B0009F3PQ2'
KEEPA_API_KEY = '4ns281h11l6th6dfg6ic193hrb0f1e65lqf64tg1b2d3bje237tnnjs1ln3veeof'

api = keepa.Keepa(KEEPA_API_KEY)


product = api.products([ASIN])['products'][0]

print(product['asin'])
print(product['title'])
print('Tokens Left:', api.tokens_left())