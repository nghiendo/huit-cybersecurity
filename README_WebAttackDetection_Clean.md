# README cho `WebAttackDetection_Clean.ipynb`

Tài liệu này giải thích toàn bộ các hàm `def` đã được dùng trong notebook:
- `WebAttackDetection_Clean.ipynb`

Mục tiêu của notebook là:
- đọc dữ liệu local trong `dataset/raw_data`
- chuẩn hóa dữ liệu text
- gộp nhiều nguồn dữ liệu web attack
- làm sạch, khử trùng lặp, kiểm tra conflict label
- train một số baseline model gọn nhẹ
- chọn model bằng validation set
- chỉ dùng test set để đánh giá cuối cùng

Notebook không:
- cài package
- tải thêm dataset
- ghi file `.csv`, `.json`, `.joblib`, `.png`
- export artifact ra ngoài

---

## 1. `sha256_text(value: str) -> str`

Vai trò:
- tạo mã băm SHA-256 từ một chuỗi text.

Notebook dùng hàm này để:
- tạo `text_hash` từ `normalized_text`
- phục vụ kiểm tra trùng lặp
- phục vụ kiểm tra label conflict trên cùng một nội dung đã chuẩn hóa
- phục vụ kiểm tra overlap giữa train / validation / test

Ý nghĩa thực tế:
- thay vì so sánh trực tiếp text dài, notebook so sánh hash cho gọn và ổn định hơn.

---

## 2. `normalize_text(value) -> str`

Vai trò:
- chuẩn hóa text đầu vào về cùng một dạng.

Hàm này làm các việc chính:
- ép dữ liệu về string
- thay ký tự null `\x00`
- loại ký tự control
- thay xuống dòng / tab bằng khoảng trắng
- gộp nhiều khoảng trắng liên tiếp thành một
- trim đầu cuối
- chuyển toàn bộ về chữ thường

Ý nghĩa thực tế:
- giúp các payload cùng nghĩa nhưng khác format được đưa về một dạng gần giống nhau
- giảm nhiễu trước khi TF-IDF học đặc trưng
- giúp dedup hiệu quả hơn

---

## 3. `clean_column_name(name: str) -> str`

Vai trò:
- làm sạch tên cột của DataFrame sau khi đọc CSV.

Hàm xử lý:
- bỏ BOM như `\ufeff`
- bỏ null byte `\x00`
- lowercase
- thay ký tự lạ bằng `_`
- bỏ `_` dư ở đầu/cuối
- nếu tên cột rỗng thì trả về `unnamed`

Ý nghĩa thực tế:
- nhiều file CSV trong dataset hiện tại có vấn đề encoding/header
- hàm này giúp đưa tên cột về dạng dễ dùng và nhất quán hơn

---

## 4. `make_unique(columns)`

Vai trò:
- đảm bảo danh sách tên cột là duy nhất.

Cách hoạt động:
- nếu tên cột bị lặp, hàm sẽ thêm hậu tố như `_1`, `_2`, ...

Ý nghĩa thực tế:
- sau bước làm sạch header, có thể có nhiều cột bị trùng tên
- pandas vẫn chạy tốt hơn khi tên cột không bị đụng nhau

---

## 5. `clean_dataframe(df: pd.DataFrame) -> pd.DataFrame`

Vai trò:
- làm sạch DataFrame ngay sau khi đọc từ CSV.

Hàm này:
- clone DataFrame để tránh sửa trực tiếp input
- chuẩn hóa toàn bộ tên cột bằng `clean_column_name`
- đảm bảo tên cột unique bằng `make_unique`
- với các cột object/string, bỏ null byte và strip khoảng trắng

Ý nghĩa thực tế:
- đây là lớp làm sạch đầu tiên ở mức bảng dữ liệu
- giúp các bước sau như tìm cột text/label ít lỗi hơn

---

## 6. `read_csv_robust(path: Path) -> pd.DataFrame`

Vai trò:
- đọc file CSV/TSV theo kiểu “chịu lỗi tốt hơn” với nhiều encoding khác nhau.

Hàm thử lần lượt các cấu hình như:
- `utf-8-sig`
- `utf-16`
- `utf-16-le`
- `utf-16-be`
- `latin1`
- dấu phân cách `,` hoặc `\t`

Nếu đọc thành công:
- hàm gọi tiếp `clean_dataframe(df)` rồi trả về DataFrame sạch.

Nếu thất bại toàn bộ:
- raise lỗi rõ ràng, cho biết file nào không đọc được.

Ý nghĩa thực tế:
- dataset hiện tại có file bị BOM/UTF-16/null-byte khá rõ
- đây là hàm quan trọng để notebook mới gọn nhưng vẫn chịu được dữ liệu bẩn

---

## 7. `find_first(columns, candidates)`

Vai trò:
- tìm tên cột đầu tiên trong `columns` mà nằm trong danh sách ứng viên `candidates`.

Notebook dùng hàm này để:
- tìm `text_col`
- tìm `label_col`

Ý nghĩa thực tế:
- các file payload không thống nhất tên cột
- hàm này giúp notebook giữ logic đơn giản mà vẫn đủ linh hoạt

---

## 8. `parse_binary_label(value, *, default=None)`

Vai trò:
- chuyển nhiều kiểu label khác nhau về bài toán nhị phân:
  - `0` = Normal
  - `1` = Attack

Hàm nhận diện các nhóm giá trị như:
- normal/benign/safe/clean/norm -> `0`
- attack/malicious/true/... -> `1`
- nếu chuỗi chứa từ khóa như `sqli`, `sql`, `xss`, `inject`, `traversal`, `command` -> `1`
- nếu không nhận diện được thì trả về `default`

Ý nghĩa thực tế:
- dùng để gom nhiều nguồn dataset khác nhau về cùng một task binary
- đơn giản hóa pipeline train/evaluate

Lưu ý:
- đây là logic quy đổi nhãn theo heuristic
- nếu sau này bạn muốn strict hơn, có thể đổi sang fail-fast cho từng dataset

---

## 9. `summarize_rows(df: pd.DataFrame, name: str)`

Vai trò:
- in tóm tắt nhanh số lượng dòng của một dataset con sau khi load.

Hàm hiển thị:
- tên file
- số dòng
- phân bố `source` và `label_name`

Ý nghĩa thực tế:
- giúp kiểm tra nhanh từng nguồn dữ liệu đã load đúng chưa
- hỗ trợ debug khi một file bị đọc sai hoặc ra số dòng bất thường

---

## 10. `load_csic_dataset(path: Path) -> pd.DataFrame`

Vai trò:
- load dataset CSIC và biến mỗi dòng thành một sample text dùng cho bài toán phát hiện tấn công web.

Cách làm chính:
1. đọc file bằng `read_csv_robust`
2. lấy cột đầu làm cột nhãn
3. lấy các cột còn lại làm nội dung request
4. với mỗi dòng:
   - parse nhãn bằng `parse_binary_label`
   - ghép các cột nội dung thành một chuỗi dạng `col=value | col=value | ...`
   - chuẩn hóa text bằng `normalize_text`
   - bỏ dòng rỗng
5. trả về DataFrame chuẩn gồm các cột:
   - `source`
   - `raw_text`
   - `label`
   - `label_name`

Ý nghĩa thực tế:
- CSIC không giống payload dataset đơn giản 1 cột text + 1 cột label
- hàm này biến dữ liệu nhiều cột thành input text thống nhất cho model

---

## 11. `load_payload_dataset(path: Path, source: str, attack_name: str) -> pd.DataFrame`

Vai trò:
- load các dataset dạng payload/text như SQLi hoặc XSS.

Cách làm chính:
1. đọc file bằng `read_csv_robust`
2. tìm cột text bằng `find_first(..., TEXT_COLUMN_CANDIDATES)`
3. tìm cột label bằng `find_first(..., LABEL_COLUMN_CANDIDATES)`
4. nếu không có text column thì báo lỗi rõ ràng
5. với mỗi dòng:
   - chuẩn hóa text bằng `normalize_text`
   - bỏ text rỗng
   - nếu có label column thì parse bằng `parse_binary_label`
   - nếu không có label column thì mặc định là attack (`1`)
6. trả về DataFrame chuẩn với format giống `load_csic_dataset`

Ý nghĩa thực tế:
- dùng chung cho nhiều file SQLi/XSS khác nhau
- giúp giảm lặp code trong notebook

---

## 12. `evaluate_frame(model, frame: pd.DataFrame, split_name: str) -> dict`

Vai trò:
- đánh giá nhanh một model trên một DataFrame bất kỳ.

Input:
- `model`: model sklearn đã train
- `frame`: DataFrame chứa `normalized_text` và `label`
- `split_name`: tên split, ví dụ `validation`

Output:
- dictionary gồm:
  - `split`
  - `accuracy`
  - `f1_macro`
  - `f1_weighted`

Ý nghĩa thực tế:
- dùng để so sánh các baseline trên validation set
- giữ phần chọn model ngắn gọn, dễ đọc

---

# Flow tổng thể của notebook

Notebook chạy theo flow sau:

1. Khai báo config và đường dẫn dữ liệu local
2. Định nghĩa helper functions để:
   - làm sạch text
   - làm sạch header
   - đọc CSV robust
   - chuẩn hóa label
3. Load từng nguồn dữ liệu:
   - CSIC
   - SQLi
   - XSS
4. Gộp tất cả thành một DataFrame chung
5. Chuẩn hóa text, tạo hash
6. Loại bỏ:
   - dòng rỗng
   - conflict label trên cùng `normalized_text`
   - duplicate theo `text_hash`
7. Split train / validation / test
8. Kiểm tra không có overlap hash giữa các split
9. Train 2 baseline model
10. Chọn model tốt nhất trên validation
11. Refit model tốt nhất trên train+validation
12. Đánh giá cuối trên test bằng:
   - classification report
   - confusion matrix

---

# Vì sao notebook mới gọn hơn notebook cũ?

Notebook mới cố tình bỏ nhiều phần để giảm rối:
- không deep learning
- không export artifact
- không logging ra file
- không download dataset ngoài
- không tạo report phụ
- không tạo nhiều figure
- không gắn vào application bundle

Kết quả là notebook tập trung vào 3 việc chính:
- load dữ liệu
- clean dữ liệu
- train/evaluate baseline rõ ràng

---

# Gợi ý nếu bạn muốn mở rộng tiếp

Nếu sau này cần mở rộng notebook mà vẫn giữ sạch, nên thêm theo từng lớp riêng:

1. `feature engineering` cell riêng
2. `model zoo` cell riêng
3. `error analysis` cell riêng
4. `cross-dataset evaluation` cell riêng
5. `export artifact` chỉ nên đặt ở notebook/script khác

Như vậy notebook chính vẫn giữ vai trò:
- ngắn
- dễ đọc
- dễ demo
- dễ sửa
