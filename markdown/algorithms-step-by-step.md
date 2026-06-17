# Các thuật toán sử dụng trong project Web Attack Detection

## 1. Mục tiêu của project
Project xây dựng pipeline phân loại request/payload web thành 4 lớp:
- Normal
- SQLi
- XSS
- OtherWebAttack

Notebook chính sử dụng nhiều nhóm thuật toán nối tiếp nhau: chuẩn hóa dữ liệu, trích xuất đặc trưng, xử lý mất cân bằng, huấn luyện nhiều mô hình, chọn mô hình tốt nhất bằng validation, rồi đánh giá cuối trên test set.

---

## 2. Quy trình tổng thể của hệ thống

### Step 1. Đọc dữ liệu từ nhiều nguồn
Project đọc dữ liệu từ các nguồn chính:
- CSIC 2010
- SQLi Extended
- SQLi
- SQLi V2
- SQLi V3
- XSS dataset

Hai hàm chính:
- `load_csic_dataset(...)`
- `load_payload_dataset(...)`

Ý tưởng:
- dữ liệu từ các nguồn có format khác nhau
- project chuyển toàn bộ về cùng một schema chung để có thể train cùng một pipeline

Schema sau chuẩn hóa gồm các trường quan trọng:
- `source`
- `raw_text`
- `label_binary`
- `label_multiclass`
- các numeric features

---

### Step 2. Làm sạch text đầu vào
Thuật toán làm sạch nằm trong `normalize_text(...)`.

Các bước:
1. ép mọi giá trị về kiểu chuỗi
2. thay null byte `\x00`
3. loại bỏ control characters
4. thay newline, carriage return, tab bằng khoảng trắng
5. gộp nhiều khoảng trắng liên tiếp thành một
6. cắt khoảng trắng đầu/cuối
7. chuyển toàn bộ sang chữ thường

Mục đích:
- giảm nhiễu cú pháp
- đưa các payload gần giống nhau về dạng gần chuẩn
- giúp TF-IDF và bước dedup hoạt động ổn định hơn

---

### Step 3. Làm sạch header và đọc CSV robust
Project không dùng cách đọc CSV quá cứng nhắc mà dùng `read_csv_robust(...)`.

Các bước:
1. thử nhiều encoding khác nhau như `utf-8-sig`, `utf-16`, `latin1`
2. thử cả dấu phân tách `,` và `\t`
3. sau khi đọc xong, làm sạch tên cột bằng `clean_column_name(...)`
4. xử lý cột bị trùng bằng `make_unique(...)`
5. strip và khử null byte ở các cột text

Thuật toán này không phải mô hình ML, nhưng là thuật toán tiền xử lý rất quan trọng vì dữ liệu gốc khá không đồng nhất.

---

### Step 4. Quy đổi nhãn về bài toán multiclass thống nhất
Project dùng `parse_binary_label(...)` để nhận diện một dòng là normal hay attack trước, sau đó ánh xạ sang nhãn multiclass.

Logic chính:
- nếu là benign/normal thì về `Normal`
- nếu là attack từ tập SQLi thì gán `SQLi`
- nếu là attack từ tập XSS thì gán `XSS`
- nếu là attack từ CSIC thì gán `OtherWebAttack`

Ý nghĩa:
- giữ được cấu trúc 4 lớp nhất quán
- gom nhiều nguồn khác nhau vào cùng một bài toán phân loại

---

### Step 5. Trích xuất đặc trưng số bằng heuristic HTTP feature extraction
Thuật toán này nằm trong `extract_http_features(...)`.

Project không chỉ dùng text raw mà còn tạo một nhóm handcrafted numerical features.

Các đặc trưng chính gồm:
- `text_length`
- `raw_length`
- `length_delta`
- số lượng `?`, `&`, `=`, quote, `;`, `-`
- số lượng dấu `<`, `>`
- số lượng dấu ngoặc
- số lượng slash
- số lượng `%`
- tỉ lệ ký tự đặc biệt
- tỉ lệ chữ số
- tỉ lệ chữ cái
- số marker encoding như `%`, `&#`
- có/không có HTTP method đầu dòng
- số lần xuất hiện từ khóa SQL
- số lần xuất hiện từ khóa script/XSS
- số lần xuất hiện từ khóa command injection
- số lần xuất hiện pattern path traversal

### Cách hoạt động step-by-step
1. nhận một chuỗi đầu vào
2. chuẩn hóa chuỗi bằng `normalize_text(...)`
3. đếm các ký tự và pattern quan trọng
4. tính ratio thay vì chỉ count tuyệt đối ở một số thuộc tính
5. trả về một dictionary feature

Ý nghĩa:
- hỗ trợ phát hiện các tấn công có pattern rõ bằng ký hiệu và từ khóa
- bổ sung thông tin mà TF-IDF text có thể chưa biểu diễn rõ

---

### Step 6. Tạo hash để kiểm tra trùng lặp và leakage
Project dùng `sha256_text(...)` để tạo `text_hash` từ `normalized_text`.

Các bước sử dụng:
1. chuẩn hóa text
2. băm SHA-256
3. dùng hash để kiểm tra xung đột nhãn
4. loại duplicate
5. kiểm tra overlap giữa train/validation/test

Mục đích:
- tránh cùng một payload xuất hiện ở nhiều split
- giảm data leakage
- đảm bảo đánh giá cuối đáng tin hơn

---

### Step 7. Loại conflict label và deduplicate
Sau khi gộp các dataset, project làm sạch ở mức dữ liệu toàn cục.

Các bước:
1. group theo `text_hash`
2. tìm những hash có nhiều hơn 1 nhãn multiclass
3. loại bỏ toàn bộ các dòng conflict
4. tiếp tục `drop_duplicates` theo `text_hash`

Ý nghĩa:
- tránh một payload giống hệt nhưng mang 2 nhãn khác nhau
- giảm nhiễu học máy
- giúp split sau đó sạch hơn

---

### Step 8. Chia tập train / validation / test theo stratified split
Project dùng `train_test_split(...)` của scikit-learn theo hai bước.

Cụ thể:
1. chia `data` thành `train_df` và `temp_df`
   - `test_size=0.30`
   - stratify theo `label_multiclass`
2. chia `temp_df` thành `val_df` và `test_df`
   - `test_size=0.50`
   - vẫn stratify

Tương đương tỉ lệ cuối:
- train: 70%
- validation: 15%
- test: 15%

Project còn kiểm tra thêm:
- overlap hash giữa train-val
- overlap hash giữa train-test
- overlap hash giữa val-test

Nếu có overlap thì assert fail.

Đây là bước quan trọng để bảo vệ quy trình đánh giá.

---

### Step 9. Xử lý mất cân bằng lớp bằng Random Oversampling
Thuật toán nằm trong `make_balanced_training_frame(...)`.

Bản chất:
- đây là oversampling ngẫu nhiên trên tập train
- class nhỏ sẽ được lấy mẫu lặp lại đến bằng class lớn nhất

### Cách hoạt động step-by-step
1. đếm số lượng mẫu của từng lớp
2. tìm `target_size = class_sizes.max()`
3. duyệt từng lớp
4. nếu lớp nào ít hơn `target_size`:
   - dùng `resample(..., replace=True, n_samples=target_size)`
5. nối tất cả nhóm lại
6. shuffle toàn bộ dữ liệu sau oversampling

Ý nghĩa:
- giảm thiên lệch về lớp lớn
- cải thiện macro-F1 cho lớp thiểu số như SQLi/XSS/OtherWebAttack

Lưu ý:
- project chỉ balance train split
- validation và test vẫn giữ phân bố tự nhiên để đánh giá công bằng hơn

---

## 3. Các mô hình học máy được sử dụng

Project huấn luyện 6 mô hình chính, gồm 4 mô hình classical và 2 mô hình deep learning.

---

## 4. Thuật toán 1: TF-IDF + Logistic Regression
Tên model:
- `logistic_regression_tfidf`

### Thành phần thuật toán
1. `TfidfVectorizer`
   - `analyzer='char_wb'`
   - `ngram_range=(3, 5)`
   - `min_df=2`
   - `max_features=100000`
2. `LogisticRegression`
   - `max_iter=1000`
   - `class_weight='balanced'`

### Step-by-step
1. lấy cột `normalized_text`
2. biến text thành vector TF-IDF trên character n-gram 3 đến 5
3. tạo ma trận đặc trưng thưa
4. Logistic Regression học trọng số cho từng class
5. dự đoán class có xác suất lớn nhất

### Vì sao dùng character n-gram
Với payload web attack, character n-gram rất hợp vì:
- bắt được pattern như `' or 1=1`
- bắt được `<script>`
- bắt được encoded tokens như `%3c`, `%27`
- bền hơn word tokenizer khi payload bị cắt vụn hoặc obfuscation

### Vai trò của Logistic Regression
- là baseline mạnh cho dữ liệu sparse
- train nhanh
- dễ ổn định
- thường hiệu quả tốt trên text classification với TF-IDF

---

## 5. Thuật toán 2: TF-IDF + Linear SVC
Tên model:
- `linear_svm_tfidf`

### Thành phần thuật toán
1. `TfidfVectorizer`
   - `analyzer='char_wb'`
   - `ngram_range=(3, 5)`
   - `min_df=2`
   - `max_features=120000`
2. `LinearSVC`
   - `class_weight='balanced'`

### Step-by-step
1. lấy `normalized_text`
2. vector hóa bằng TF-IDF character n-gram
3. Linear SVC tìm siêu phẳng tuyến tính tách các lớp
4. chọn class theo decision score lớn nhất

### Ý nghĩa
- SVM tuyến tính thường mạnh trên không gian đặc trưng sparse rất lớn
- phù hợp với text classification và pattern recognition trong payload

Khác với Logistic Regression:
- Logistic Regression tối ưu xác suất/log-loss
- Linear SVC tối ưu margin phân tách

---

## 6. Thuật toán 3: Statistical Features + Random Forest
Tên model:
- `statistical_features_random_forest`

### Thành phần thuật toán
1. `StandardScaler()`
2. `RandomForestClassifier`
   - `n_estimators=300`
   - `class_weight='balanced_subsample'`
   - `n_jobs=-1`

### Step-by-step
1. lấy toàn bộ `NUMERIC_FEATURE_COLS`
2. điền giá trị thiếu bằng `0`
3. chuẩn hóa thang đo numeric features
4. train Random Forest gồm nhiều cây quyết định
5. mỗi cây học các rule tách dựa trên feature heuristic
6. bỏ phiếu để ra class cuối

### Ý nghĩa
Mô hình này không đọc text trực tiếp mà dựa vào dấu hiệu thống kê như:
- nhiều dấu quote
- nhiều SQL keywords
- nhiều angle brackets
- nhiều traversal patterns

Điểm mạnh:
- dễ bắt các rule heuristic mạnh
- đôi lúc tốt với tấn công có pattern thủ công rõ ràng

---

## 7. Thuật toán 4: Multi-view TF-IDF + Statistical Features + Logistic Regression
Tên model:
- `multiview_tfidf_stats_logistic_regression`

### Thành phần thuật toán
1. `ColumnTransformer`
   - nhánh text: `TfidfVectorizer(...)`
   - nhánh numeric: `StandardScaler()`
2. `LogisticRegression`

### Step-by-step
1. chuẩn bị input gồm:
   - `normalized_text`
   - `NUMERIC_FEATURE_COLS`
2. `ColumnTransformer` xử lý riêng từng nhánh:
   - text -> TF-IDF char n-gram
   - numeric -> scale
3. ghép hai khối đặc trưng lại thành một vector chung
4. Logistic Regression học trên vector hợp nhất
5. dự đoán lớp đầu ra

### Ý nghĩa của multi-view
- view 1: hiểu pattern ký tự trong payload
- view 2: hiểu thống kê cú pháp/tín hiệu heuristic
- kết hợp hai góc nhìn giúp mô hình cân bằng giữa nội dung và cấu trúc

---

## 8. Thuật toán 5: CNN + BiLSTM cho text
Tên model:
- `cnn_bilstm_text`

Đây là mô hình deep learning chỉ dùng text.

### Kiến trúc
1. `TextVectorization`
2. `Embedding(input_dim=50000, output_dim=64)`
3. `Conv1D(filters=96, kernel_size=5, activation='relu')`
4. `MaxPooling1D(pool_size=2)`
5. `Bidirectional(LSTM(64))`
6. `Dropout(0.35)`
7. `Dense(64, activation='relu')`
8. `Dropout(0.25)`
9. `Dense(num_classes, activation='softmax')`

### Step-by-step
1. mã hóa nhãn bằng `LabelEncoder`
2. `TextVectorization` học vocabulary từ train set
3. chuyển text thành chuỗi token id có độ dài cố định 256
4. `Embedding` ánh xạ token id sang vector dense
5. `Conv1D` học local patterns trong chuỗi ký tự/token
6. `MaxPooling1D` giảm chiều và giữ đặc trưng mạnh
7. `BiLSTM` đọc ngữ cảnh hai chiều để học quan hệ tuần tự
8. `Dense + Softmax` tạo xác suất cho 4 lớp
9. huấn luyện bằng Adam và `sparse_categorical_crossentropy`
10. dừng sớm bằng `EarlyStopping(monitor='val_loss', patience=3)`

### Vai trò của từng khối
- `TextVectorization`: biến text thô thành token sequence
- `Embedding`: học biểu diễn dense
- `Conv1D`: bắt pattern cục bộ như chuỗi ký tự tấn công
- `BiLSTM`: học thứ tự và ngữ cảnh của chuỗi
- `Softmax`: phân loại multiclass

---

## 9. Thuật toán 6: Multi-view CNN-BiLSTM + Statistical Branch
Tên model:
- `multiview_cnn_bilstm_text_stats`

Đây là mô hình deep learning kết hợp text branch và numeric branch.

### Kiến trúc nhánh text
1. `TextVectorization`
2. `Embedding`
3. `Conv1D`
4. `MaxPooling1D`
5. `Bidirectional(LSTM)`
6. `Dropout`

### Kiến trúc nhánh numeric
1. `StandardScaler`
2. `Dense(64, relu)`
3. `Dropout(0.25)`
4. `Dense(32, relu)`

### Hợp nhất
1. `Concatenate()` hai nhánh
2. `Dense(96, relu)`
3. `Dropout(0.30)`
4. `Dense(num_classes, softmax)`

### Step-by-step
1. mã hóa nhãn bằng `LabelEncoder`
2. scale numeric features bằng `StandardScaler`
3. vectorize text bằng `TextVectorization`
4. text branch học pattern tuần tự
5. stats branch học tín hiệu heuristic dạng số
6. nối hai vector biểu diễn lại
7. đưa qua dense layers để học tương tác giữa 2 view
8. softmax xuất ra xác suất 4 lớp
9. train với Adam + early stopping theo `val_loss`

### Ý nghĩa
Đây là mô hình tổng hợp mạnh nhất về mặt ý tưởng vì:
- vừa đọc payload raw
- vừa đọc thống kê heuristic
- có khả năng học cả đặc trưng tự động lẫn đặc trưng thủ công

---

## 10. Thuật toán đánh giá mô hình
Project dùng hai helper chính:
- `evaluate_frame(...)` cho sklearn/classical model
- `evaluate_deep_predictions(...)` cho deep model

### Chỉ số đánh giá
- Accuracy
- F1 macro
- F1 weighted

### Vì sao dùng F1 macro
Bài toán có mất cân bằng lớp, nên chỉ nhìn accuracy là chưa đủ.
F1 macro giúp đo hiệu quả đều trên tất cả class, đặc biệt quan trọng với các lớp thiểu số.

---

## 11. Thuật toán chọn mô hình tốt nhất
Sau khi train toàn bộ model trên `train_balanced_df`, project tạo `validation_table` rồi sắp xếp theo:
1. `f1_macro` giảm dần
2. nếu bằng nhau thì `accuracy` giảm dần

Model đứng đầu được gán cho `best_model_name`.

Ý nghĩa:
- ưu tiên khả năng cân bằng giữa các lớp
- accuracy chỉ dùng làm tiêu chí phụ

---

## 12. Thuật toán huấn luyện cuối cùng trước khi test
Sau khi chọn best model:
1. gộp `train_df + val_df` thành `trainval_df`
2. rebalance lại thành `trainval_balanced_df`
3. train lại model tốt nhất trên tập lớn hơn
4. predict trên `test_df`
5. in `classification_report`
6. vẽ `confusion_matrix`

Đây là giai đoạn final evaluation.

---

## 13. Tóm tắt vai trò từng nhóm thuật toán

### Nhóm tiền xử lý
- `normalize_text`
- `clean_dataframe`
- `read_csv_robust`
- `sha256_text`

Vai trò:
- làm sạch dữ liệu
- chuẩn hóa input
- chống duplicate/leakage

### Nhóm feature engineering
- `extract_http_features`

Vai trò:
- biến dấu hiệu bảo mật web thành numeric features

### Nhóm xử lý imbalance
- `make_balanced_training_frame`
- random oversampling bằng `resample`

Vai trò:
- tăng số mẫu cho lớp thiểu số

### Nhóm mô hình classical
- TF-IDF + Logistic Regression
- TF-IDF + Linear SVC
- Random Forest trên numeric features
- Multi-view Logistic Regression

Vai trò:
- tạo baseline mạnh, dễ train, dễ so sánh

### Nhóm mô hình deep learning
- CNN + BiLSTM text-only
- Multi-view CNN + BiLSTM + stats

Vai trò:
- học biểu diễn đặc trưng tự động sâu hơn từ dữ liệu

---

## 14. Kết luận
Project này không dùng một thuật toán duy nhất, mà là một pipeline nhiều tầng:
1. đọc và làm sạch dữ liệu nhiều nguồn
2. chuẩn hóa text
3. trích xuất handcrafted HTTP/security features
4. loại duplicate và conflict label
5. chia train/validation/test có kiểm tra leakage
6. oversampling để xử lý mất cân bằng lớp
7. train nhiều mô hình classical và deep learning
8. chọn mô hình tốt nhất bằng validation
9. train lại trên `train + validation`
10. đánh giá cuối trên test set

Nếu nhìn theo góc độ học máy, ba ý tưởng cốt lõi nhất của project là:
- character-level text representation bằng TF-IDF hoặc deep sequence model
- handcrafted security features từ payload HTTP
- multi-view learning kết hợp text và numeric signals
