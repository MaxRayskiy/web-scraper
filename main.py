import requests
from bs4 import BeautifulSoup
import time
import sqlite3

BOOK_PAGE_SCRAPE_TIMEOUT_SECONDS = 0
NEXT_PAGE_TIMEOUT_SECONDS = 6
PAGES_TO_SCRAPE_CNT = 2
BASE_URL = "http://books.toscrape.com"
DATABASE_NAME = "bookstore.db"
ENABLE_DB_WRITE = False # @todo


def write_to_sqlite(data_list, database_name=DATABASE_NAME):
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price REAL,
            rating INTEGER,
            stock INTEGER,
            upc TEXT
        )
    ''')

    for data in data_list:
        cursor.execute('''
            INSERT INTO books (title, price, rating, stock, upc)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['Title'], data['Price'], data['Rating'], data['Stock'], data['UPC']))

    conn.commit()
    conn.close()


def scrape_page_with_books(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    books = soup.find_all('article', class_='product_pod')

    data_list = []

    for book in books:
        title = book.h3.a['title']
        price = float(book.select('div p.price_color')[0].text.strip('Â£'))
        rating = book.select('p[class^="star-rating"]')[0]['class'][1]

        if ".html" not in url:
            book_url = url + '/' + book.h3.a['href']
        else:
            book_url = url[:url.rfind('/')] + '/' + book.h3.a['href']
        book_response = requests.get(book_url)
        book_soup = BeautifulSoup(book_response.text, 'html.parser')

        stock = book_soup.find('p', class_='instock availability').text.strip()
        if "In stock" not in stock:
            stock_val = 0
        else:
            stock_val = int(stock.split("(")[-1].split(")")[0].split()[0])
        upc = book_soup.find('th', text='UPC').find_next('td').text.strip()

        data_list.append({'Title': title, 'Price': price, 'Rating': rating, 'Stock': stock_val, 'UPC': upc})
        time.sleep(BOOK_PAGE_SCRAPE_TIMEOUT_SECONDS)

    return data_list


def get_next_page_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    next_page = soup.find('li', class_='next')
    if next_page:
        return BASE_URL + '/' + next_page.a['href']
    else:
        return None


if __name__ == "__main__":
    current_url = BASE_URL
    all_data = []

    for _ in range(PAGES_TO_SCRAPE_CNT):
        data = scrape_page_with_books(current_url)
        if ENABLE_DB_WRITE:
            write_to_sqlite(data)
        else:
            all_data.extend(data)
        current_url = get_next_page_url(current_url)

    if not ENABLE_DB_WRITE:
        for book in all_data[:10]:
            print(book)
