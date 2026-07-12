from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv
import re
import time

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--lang=vi-VN")
options.add_experimental_option("prefs", {
    "intl.accept_languages": "vi,vi_VN",
    "profile.default_content_setting_values.geolocation": 2
})
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

QUERY = "nhà hàng quận Thủ Đức"
OUTPUT_FILE = "restaurant_detail.csv"
MAX_TEST = None  # set số lượng nhà hàng muốn test, None = tất cả

SEARCH_BOX_XPATH = "//input[@name='q' and @role='combobox']"
SEARCH_BTN_XPATH = "//button[@aria-label='Tìm kiếm']"


def search_restaurants():
    driver.get("https://www.google.com/maps")
    time.sleep(4)
    try:
        consent_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[contains(text(),'Accept all') or contains(text(),'Chấp nhận tất cả') or contains(text(),'Tôi đồng ý')]]"
            ))
        )
        consent_btn.click()
        time.sleep(2)
    except Exception:
        pass

    search_box = wait.until(EC.element_to_be_clickable((By.XPATH, SEARCH_BOX_XPATH)))
    search_box.click()
    search_box.clear()
    for ch in QUERY:
        search_box.send_keys(ch)
        time.sleep(0.05)
    time.sleep(1)

    search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, SEARCH_BTN_XPATH)))
    search_btn.click()
    time.sleep(4)

    scrollable_div = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))

    last_count = 0
    same_count = 0
    max_rounds = 200  # tăng số vòng để đủ thời gian load tới khi Google dừng trả thêm

    for round_i in range(max_rounds):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(1.5)

        # Đếm số kết quả hiện có thay vì chỉ dựa vào scrollHeight
        current_links = scrollable_div.find_elements(By.XPATH, ".//a[contains(@href, '/maps/place')]")
        current_count = len(current_links)

        # Kiểm tra có dòng "Bạn đã xem hết danh sách" hay chưa (Google báo hết kết quả)
        try:
            end_marker = scrollable_div.find_elements(
                By.XPATH, ".//*[contains(text(),'đã đến cuối danh sách') or contains(text(),'You\\'ve reached the end')]"
            )
        except Exception:
            end_marker = []

        if end_marker:
            print(f"[SEARCH] Đã đến cuối danh sách sau {round_i+1} vòng scroll")
            break

        if current_count == last_count:
            same_count += 1
            if same_count >= 5:  # tăng ngưỡng chắc chắn hơn (5 lần liên tiếp không tăng)
                print(f"[SEARCH] Dừng scroll: không tăng thêm kết quả sau {same_count} lần thử")
                break
        else:
            same_count = 0
        last_count = current_count

    elements = scrollable_div.find_elements(By.XPATH, ".//a[contains(@href, '/maps/place')]")
    results = []
    seen_href = set()
    for el in elements:
        href = el.get_attribute("href")
        name = el.get_attribute("aria-label")
        if href and href not in seen_href and name:
            seen_href.add(href)
            results.append({"name": name, "href": href})

    print(f"[SEARCH] Thu thập được {len(results)} link nhà hàng")
    return results


def extract_lat_lng(href):
    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", href)
    if m:
        return m.group(1), m.group(2)
    return None, None


def extract_address():
    """Lấy text địa chỉ, bỏ icon: trỏ thẳng vào div chứa text bên trong button,
    không lấy .text của cả button (dễ dính icon nếu icon có aria-label/alt text)."""
    try:
        btn = driver.find_element(By.XPATH, "//button[@data-item-id='address']")
        # Ưu tiên lấy div con cuối cùng (thường là div chứa text thật, icon là div/svg đầu)
        inner_divs = btn.find_elements(By.XPATH, ".//div")
        candidates = [d.text.strip() for d in inner_divs if d.text.strip()]
        print(f"    [DEBUG address] candidates từ inner div: {candidates}")
        if candidates:
            full_address = candidates[-1]  # lấy dòng text dài nhất/cuối cùng
        else:
            full_address = btn.text.strip()
    except Exception as e:
        print(f"    [DEBUG address] lỗi: {e}")
        full_address = None
    return full_address


def parse_address(full_address):
    if not full_address:
        return None, None, None
    parts = [p.strip() for p in full_address.split(",")]
    street = parts[0] if len(parts) >= 1 else None
    district = parts[-2] if len(parts) >= 2 else None
    city = parts[-1] if len(parts) >= 1 else None
    return street, district, city


def extract_rating_and_reviews():
    rating, reviews = None, None
    try:
        panel_text = driver.find_element(By.XPATH, "//div[@role='main']").text
        # VD: "4,5" rồi "(133)" nằm gần nhau ở đầu panel
        m = re.search(r"(\d[.,]\d)\D{0,15}?\(([\d.,]+)\)", panel_text)
        if m:
            rating, reviews = m.group(1), m.group(2)
    except Exception as e:
        print(f"    [DEBUG rating] lỗi: {e}")
    return rating, reviews

def get_panel_full_text():
    """Lấy toàn bộ text kể cả phần chưa hiện trong viewport, dùng JS textContent
    thay vì Selenium .text (Selenium .text chỉ lấy phần render trong viewport)."""
    try:
        panel = driver.find_element(By.XPATH, "//div[@role='main']")
        text = driver.execute_script("return arguments[0].textContent;", panel)
        return text
    except Exception as e:
        print(f"    [DEBUG panel] Lỗi lấy full text: {e}")
        return ""

def parse_price_number(raw):
    """Bỏ dấu chấm ngăn cách nghìn, trả về chuỗi số thuần."""
    return raw.replace('.', '').replace(',', '').strip()

def extract_price_range():
    min_p, max_p = None, None
    panel_text = get_panel_full_text()

    # Dạng A: "200-800 N đ" — cả 2 số đều viết tắt theo nghìn, nhân 1000
    m = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)\s*N\s*[đĐ₫]", panel_text)
    if m:
        min_p = str(int(parse_price_number(m.group(1))) * 1000)
        max_p = str(int(parse_price_number(m.group(2))) * 1000)
        print(f"    [DEBUG price] ✔ (dạng N đ) {min_p} - {max_p}")
        return min_p, max_p

    # Dạng B: "1-600.000 đ" — số đã đầy đủ, dấu chấm chỉ là phân cách nghìn, KHÔNG nhân thêm
    m2 = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)\s*[đĐ₫](?!\s*/)", panel_text)
    if m2:
        min_p = parse_price_number(m2.group(1))
        max_p = parse_price_number(m2.group(2))
        print(f"    [DEBUG price] ✔ (dạng đầy đủ) {min_p} - {max_p}")
        return min_p, max_p

    # Fallback: dạng cũ "đ/người"
    m3 = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)\s*đ\s*/\s*người", panel_text)
    if m3:
        min_p, max_p = parse_price_number(m3.group(1)), parse_price_number(m3.group(2))
    else:
        print("    [DEBUG price] ✘ Vẫn không khớp được giá")

    return min_p, max_p

    # fallback nếu có quán dùng định dạng cũ "đ/người"
    m2 = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)\s*đ\s*/\s*người", panel_text)
    if m2:
        min_p, max_p = m2.group(1), m2.group(2)
    else:
        print("    [DEBUG price] ✘ Không khớp được giá")

    return min_p, max_p

def extract_hours():
    """Lấy trạng thái mở/đóng cửa và giờ hoạt động hôm nay."""
    is_open = None
    try:
        panel_text = driver.find_element(By.XPATH, "//div[@role='main']").text
        if "Đang mở cửa" in panel_text or "Mở cả ngày" in panel_text:
            is_open = True
        elif "Đã đóng cửa" in panel_text or "Sắp mở cửa" in panel_text:
            is_open = False

    except Exception:
        pass
    return is_open


def extract_full_week_hours():
    full_hours = None
    try:
        # Bấm chính xác vào MŨI TÊN mở rộng bên phải, không bấm cả dòng
        arrow_btn = driver.find_element(
            By.XPATH,
            "//*[@aria-label='Hiện giờ mở cửa trong tuần' or @aria-label='Ẩn giờ mở cửa trong tuần']"
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", arrow_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", arrow_btn)
        time.sleep(1)
        print("    [DEBUG hours] ✔ Đã bấm vào mũi tên mở giờ")
    except Exception as e:
        print(f"    [DEBUG hours] ✘ Không tìm/bấm được mũi tên: {e}")
        # Fallback: nếu không tìm thấy mũi tên (có thể site đổi cấu trúc), thử bấm cả dòng như cũ
        try:
            hour_row = driver.find_element(
                By.XPATH,
                "//*[contains(text(),'Đang đóng cửa') or contains(text(),'Đang mở cửa') "
                "or contains(text(),'Đã đóng cửa') or contains(text(),'Xem thêm giờ')]"
            )
            clickable = driver.execute_script("""
                let el = arguments[0];
                while (el && el.tagName !== 'BUTTON' && !el.getAttribute('jsaction')) {
                    el = el.parentElement;
                }
                return el;
            """, hour_row)
            target = clickable if clickable else hour_row
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
            print("    [DEBUG hours] ✔ Đã bấm fallback vào dòng giờ")
        except Exception as e2:
            print(f"    [DEBUG hours] ✘ Fallback cũng lỗi: {e2}")

    panel_text = get_panel_full_text()
    day_pattern = re.compile(
        r"(Thứ\s*(?:Hai|Ba|Tư|Năm|Sáu|Bảy)|Chủ\s*Nhật)\s*"
        r"(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})"
    )
    matches = day_pattern.findall(panel_text)

    if matches:
        cleaned = [(re.sub(r"\s+", " ", d).strip(), t.strip()) for d, t in matches]
        full_hours = " | ".join(f"{d} {t}" for d, t in cleaned)
        print(f"    [DEBUG hours] ✔ {full_hours}")
    else:
        print("    [DEBUG hours] ✘ Vẫn không tìm được, in 400 ký tự đầu panel:")
        print("     ", panel_text[:400])

    return full_hours


KNOWN_SERVICES = {
    "Ăn tại chỗ", "Đồ ăn mang đi", "Giao hàng", "Không giao hàng",
    "Phục vụ ăn sáng", "Phục vụ bữa trưa", "Phục vụ bữa tối",
    "Có chỗ ngồi ngoài trời", "Wi-Fi miễn phí", "Chấp nhận đặt trước",
    "Phù hợp với trẻ em", "Có chỗ đậu xe", "Phục vụ đồ uống có cồn",
}

def extract_services():
    services = []
    try:
        result = driver.execute_script("""
            let groups = document.querySelectorAll('div.LTs0Rc[role="group"]');
            let out = [];
            groups.forEach(g => {
                let textDiv = g.querySelector('div[aria-hidden="true"]');
                if (textDiv) {
                    let t = textDiv.textContent.trim();
                    if (t) out.push(t);
                }
            });
            return out;
        """)
        seen = set()
        for t in result:
            if t not in seen:
                seen.add(t)
                services.append(t)
        print(f"    [DEBUG service] ✔ {services}")

        if not services:
            print("    [DEBUG service] ✘ Không tìm thấy 'LTs0Rc', thử click nút mở rộng...")
            try:
                expand_btn = driver.find_element(By.XPATH, "//button[contains(@class,'XJ8h0e')]")
                driver.execute_script("arguments[0].click();", expand_btn)
                time.sleep(0.5)
                result2 = driver.execute_script("""
                    let groups = document.querySelectorAll('div[role="group"]');
                    let out = [];
                    groups.forEach(g => {
                        let textDiv = g.querySelector('div[aria-hidden="true"]');
                        if (textDiv) {
                            let t = textDiv.textContent.trim();
                            if (t) out.push(t);
                        }
                    });
                    return out;
                """)
                for t in result2:
                    if t and t not in services:
                        services.append(t)
                print(f"    [DEBUG service] sau khi click ✔ {services}")
            except Exception as e2:
                print(f"    [DEBUG service] click mở rộng lỗi: {e2}")

    except Exception as e:
        print(f"    [DEBUG service] lỗi: {e}")

    return services


def scroll_detail_panel_fully(panel):
    """Scroll panel chi tiết tới khi hết nội dung mới load ra,
    tương tự cách đã làm với danh sách kết quả search."""
    last_height = 0
    same_count = 0
    for i in range(15):  # tối đa 15 lần, đủ cho hầu hết panel chi tiết
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
        time.sleep(1)
        new_height = driver.execute_script("return arguments[0].scrollHeight", panel)
        if new_height == last_height:
            same_count += 1
            if same_count >= 2:
                break
        else:
            same_count = 0
        last_height = new_height
    print(f"    [DEBUG scroll] Đã scroll {i+1} lần, chiều cao cuối: {last_height}")

def extract_image_url():
    try:
        img = driver.find_element(
            By.XPATH,
            "//img[contains(@src,'googleusercontent.com')]"
        )
        return img.get_attribute("src")
    except Exception:
        return None

def scrape_detail(item, idx):
    href = item["href"]
    name = item["name"]

    driver.get(href)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1")))
    except Exception:
        print(f"  ✘ Không load được trang chi tiết cho: {name}")
    time.sleep(2)

    # --- Scroll đầy đủ TRƯỚC khi trích xuất bất kỳ thông tin gì ---
    try:
        panel = driver.find_element(By.XPATH, "//div[@role='main']")
        scroll_detail_panel_fully(panel)
    except Exception as e:
        print(f"    [DEBUG scroll] Lỗi tìm/scroll panel: {e}")

    # In ra toàn bộ text panel SAU KHI scroll để kiểm tra có "đ/người" và "Thứ" chưa
    try:
        panel_text_check = driver.find_element(By.XPATH, "//div[@role='main']").text
        print(f"    [DEBUG panel] Có 'đ/người': {'đ/người' in panel_text_check}")
        print(f"    [DEBUG panel] Có chữ 'Thứ': {'Thứ' in panel_text_check}")
    except Exception:
        pass

    # Lấy giờ mở cửa TRƯỚC khi scroll toàn panel, tránh DOM bị unmount
    is_open = extract_hours()
    open_time_full = extract_full_week_hours()
    lat, lng = extract_lat_lng(driver.current_url)
    full_address = extract_address()
    street, district, city = parse_address(full_address)
    rating, reviews = extract_rating_and_reviews()
    min_price, max_price = extract_price_range()
    services = extract_services()
    image_url = extract_image_url()
    restaurant_id = str(idx + 1).zfill(6)

    row = {
        "restaurant_id": restaurant_id,
        "restaurant_name": name,
        "address": street,
        "district": district,
        "city": city,
        "latitude": lat,
        "longitude": lng,
        "total_reviews": reviews,
        "avg_rating": rating,
        "min_price": min_price,
        "max_price": max_price,
        "open_time": open_time_full,
        "is_open": is_open,
        "service": ";".join(services) if services else None,
        "image_url": image_url,
    }

    print(f"  [{restaurant_id}] {name}")
    print(f"    address={full_address} -> street={street}, district={district}, city={city}")
    print(f"    rating={rating}, reviews={reviews}, price=({min_price},{max_price})")
    print(f"    open_time={open_time_full}")

    driver.save_screenshot(f"debug_detail_{restaurant_id}.png")
    with open(f"debug_detail_{restaurant_id}.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    return row


# ============ MAIN ============
restaurant_list = search_restaurants()
if MAX_TEST is not None:
    restaurant_list = restaurant_list[:MAX_TEST]

rows = []
for idx, item in enumerate(restaurant_list):
    print(f"\n→ Đang xử lý ({idx+1}/{len(restaurant_list)}): {item['name']}")
    for attempt in range(2):  # thử tối đa 2 lần nếu lỗi
        try:
            rows.append(scrape_detail(item, idx))
            break
        except Exception as e:
            print(f"  ✘ Lỗi lần {attempt+1} khi cào {item['name']}: {e}")
            time.sleep(2)
    else:
        print(f"  ✘✘ Bỏ qua {item['name']} sau 2 lần thử thất bại")

fieldnames = [
    "restaurant_id", "restaurant_name", "address", "district", "city",
    "latitude", "longitude", "total_reviews", "avg_rating",
    "min_price", "max_price", "open_time", "is_open", "service", "image_url"
]

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✔ Đã lưu {len(rows)} dòng vào {OUTPUT_FILE}")
time.sleep(20)
driver.quit()