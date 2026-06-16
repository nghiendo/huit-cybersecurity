# Kỹ thuật xử lý data imbalance

Tài liệu này giải thích ngắn gọn các kỹ thuật xử lý dữ liệu mất cân bằng (data imbalance), kèm ví dụ thực tế theo ngữ cảnh notebook hiện tại của project.

## 1. Data imbalance là gì?

Data imbalance xảy ra khi số lượng mẫu giữa các class chênh lệch lớn.

Ví dụ:
- Class `SQLi`: có thể rất lớn khi gộp nhiều bộ SQL injection
- Class `XSS`: thường nhỏ hơn đáng kể
- Class `OtherWebAttack` từ CSIC có thể nhỏ hơn `SQLi` sau khi gộp toàn bộ dữ liệu

Khi đó model dễ học theo hướng:
- ưu tiên class lớn
- bỏ qua class nhỏ
- accuracy có thể vẫn cao, nhưng recall/F1 của class hiếm rất thấp

Ví dụ đơn giản:
- 95 mẫu `Normal`
- 5 mẫu `Attack`
- nếu model luôn đoán `Normal`, accuracy vẫn là 95%
- nhưng model hoàn toàn vô dụng cho việc phát hiện tấn công

Vì vậy, với data imbalance, không nên chỉ nhìn accuracy.

---

## 2. Dấu hiệu nhận biết data imbalance

Các dấu hiệu phổ biến:
- biểu đồ phân bố class lệch mạnh
- một vài class có ít mẫu hơn class lớn nhất rất nhiều lần
- confusion matrix cho thấy class nhỏ bị đoán nhầm hàng loạt
- macro F1 thấp hơn weighted F1 khá xa

Trong bài toán multiclass web attack, cần đặc biệt chú ý vì:
- `SQLi` thường có rất nhiều mẫu
- `XSS` ít hơn
- `OtherWebAttack` từ CSIC là một class attack tổng quát, nhưng khi gộp với SQLi/XSS thì vẫn có thể bị lệch phân bố theo hướng khác với `Normal`

---

## 3. Các kỹ thuật xử lý data imbalance

### 3.1. Stratified split

Mục tiêu:
- giữ tỷ lệ class tương đối giống nhau giữa train / validation / test

Ý nghĩa:
- tránh tình trạng một split gần như không có mẫu của class hiếm

Ví dụ:
```python
from sklearn.model_selection import train_test_split

train_df, temp_df = train_test_split(
    data,
    test_size=0.30,
    random_state=42,
    stratify=data["label_multiclass"],
)

val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    random_state=42,
    stratify=temp_df["label_multiclass"],
)
```

Lưu ý:
- stratify không làm dữ liệu cân bằng hơn
- nó chỉ giữ tỷ lệ class ổn định giữa các split

---

### 3.2. Oversampling class thiểu số

Mục tiêu:
- tăng số lượng mẫu của class nhỏ bằng cách lặp lại mẫu có sẵn

Cách làm cơ bản:
- lấy class lớn nhất làm chuẩn
- với các class nhỏ hơn, random sample có hoàn lại (`replace=True`) cho tới khi bằng class lớn nhất

Ví dụ:
```python
import pandas as pd
from sklearn.utils import resample


def make_balanced_training_frame(frame: pd.DataFrame, label_col: str = "label_multiclass") -> pd.DataFrame:
    groups = []
    class_sizes = frame[label_col].value_counts()
    target_size = class_sizes.max()

    for label, group in frame.groupby(label_col):
        if len(group) < target_size:
            sampled = resample(
                group,
                replace=True,
                n_samples=target_size,
                random_state=42,
            )
            groups.append(sampled)
        else:
            groups.append(group)

    balanced = pd.concat(groups, ignore_index=True)
    return balanced.sample(frac=1.0, random_state=42).reset_index(drop=True)
```

Ví dụ trước và sau oversampling:
- trước:
  - Normal: 10,000
  - SQLi: 50,000
  - XSS: 3,000
  - OtherWebAttack: 8,000
- sau:
  - Normal: 50,000
  - SQLi: 50,000
  - XSS: 50,000
  - OtherWebAttack: 50,000

Ưu điểm:
- đơn giản
- dễ hiểu
- thường cải thiện recall cho class hiếm

Nhược điểm:
- lặp lại mẫu cũ nên dễ overfit
- không tạo thông tin mới thực sự

---

### 3.3. Undersampling class đa số

Mục tiêu:
- giảm bớt số lượng mẫu của class lớn

Ví dụ:
- Normal: 100,000
- SQLi: 80,000
- XSS: 5,000
- OtherWebAttack: 3,000

Có thể cắt bớt:
- Normal xuống 10,000
- SQLi xuống 10,000

Ví dụ code:
```python
from sklearn.utils import resample

majority = df[df["label"] == "SQLi"]
minority = df[df["label"] == "XSS"]

majority_downsampled = resample(
    majority,
    replace=False,
    n_samples=len(minority),
    random_state=42,
)

balanced_df = pd.concat([majority_downsampled, minority])
```

Ưu điểm:
- giảm thiên lệch về class lớn
- train nhanh hơn

Nhược điểm:
- mất dữ liệu
- có thể bỏ mất pattern quan trọng ở class lớn

Trong bài toán text security, undersampling mạnh thường không phải lựa chọn đầu tiên nếu dữ liệu class lớn vẫn chứa nhiều pattern đa dạng.

---

### 3.4. Class weights

Mục tiêu:
- phạt nặng hơn khi model dự đoán sai ở class hiếm

Ý tưởng:
- thay vì sửa dữ liệu đầu vào, ta sửa hàm loss hoặc trọng số học

Ví dụ với Logistic Regression và Linear SVC:
```python
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

logreg = LogisticRegression(
    max_iter=1200,
    class_weight="balanced",
    random_state=42,
)

svm = LinearSVC(
    class_weight="balanced",
    random_state=42,
)
```

Ý nghĩa của `class_weight="balanced"`:
- sklearn tự tăng trọng số cho class ít mẫu
- class càng hiếm thì lỗi dự đoán sai càng bị phạt mạnh

Ưu điểm:
- rất gọn
- thường hiệu quả tốt cho baseline
- không cần nhân bản dữ liệu

Nhược điểm:
- có thể chưa đủ nếu class quá hiếm
- phụ thuộc vào thuật toán hỗ trợ `class_weight`

---

### 3.5. Kết hợp oversampling + class weights

Đây là cách đang dùng trong notebook hiện tại.

Ý tưởng:
- oversampling giúp model nhìn thấy class hiếm nhiều hơn
- class weights giúp loss chú ý hơn tới class hiếm

Ví dụ:
```python
train_balanced_df = make_balanced_training_frame(train_df)

model.fit(
    train_balanced_df["normalized_text"],
    train_balanced_df["label_multiclass"],
)
```

với model:
```python
Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))),
    ("clf", LogisticRegression(class_weight="balanced", max_iter=1200, random_state=42)),
])
```

Ưu điểm:
- mạnh hơn dùng riêng từng kỹ thuật
- phù hợp cho baseline multiclass với text data

Nhược điểm:
- vẫn có thể overfit class nhỏ nếu oversampling quá mạnh

---

### 3.6. SMOTE và các biến thể

Mục tiêu:
- sinh thêm mẫu mới cho class hiếm thay vì chỉ lặp lại mẫu cũ

Phổ biến trong dữ liệu tabular số học.

Ví dụ:
```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
```

Lưu ý quan trọng với text:
- SMOTE không áp dụng trực tiếp tốt trên raw text string
- thường phải vectorize trước
- với TF-IDF sparse vector, dùng SMOTE cần cân nhắc kỹ vì dữ liệu rất high-dimensional và thưa

Với bài toán NLP/text detection baseline, oversampling ở mức sample hoặc class_weight thường thực tế hơn nhiều.

---

### 3.7. Data augmentation

Mục tiêu:
- tăng dữ liệu class hiếm bằng cách tạo biến thể mới

Ví dụ trong text:
- synonym replacement
- back translation
- paraphrase
- chèn/xóa token nhẹ

Ví dụ trong security text:
- biến đổi encoding payload
- đổi khoảng trắng
- đổi quote style
- đổi case
- đổi cách comment SQL

Ví dụ:
- `' OR 1=1 --`
- `" or 1 = 1 --`
- `%27%20or%201%3D1--`

Ưu điểm:
- tăng đa dạng dữ liệu
- giúp model bớt overfit vào exact string

Nhược điểm:
- augmentation kém chất lượng có thể sinh nhãn sai
- cần hiểu domain security để biến đổi hợp lý

---

## 4. Khi nào imbalance “không quá nguy hiểm”?

Imbalance không phải lúc nào cũng là thảm họa.

Có thể chấp nhận hơn nếu:
- class hiếm vẫn có đủ số mẫu tuyệt đối
- pattern giữa các class tách biệt rất mạnh
- mục tiêu là ranking hoặc anomaly screening sơ bộ
- metric chính là macro F1 / per-class recall và các giá trị này vẫn tốt

Ví dụ:
- nếu class `XSS` chỉ ít hơn `SQLi`, nhưng payload XSS có pattern rất đặc trưng như `<script>`, `onerror=`, `javascript:`,
  thì model vẫn có thể học tốt dù lệch lớp.

Nhưng với notebook hiện tại, tôi không coi imbalance là “không thành vấn đề”, vì:
- số mẫu giữa 4 lớp lệch đáng kể
- `SQLi` đang là class rất lớn khi gộp nhiều nguồn dữ liệu
- `XSS` và `OtherWebAttack` có thể bị lép vế hơn nếu không xử lý cẩn thận

---

## 5. Nên đánh giá bằng metric nào?

Khi dữ liệu imbalance, nên nhìn:
- macro F1
- weighted F1
- per-class precision
- per-class recall
- confusion matrix

Không nên chỉ nhìn:
- accuracy

Ví dụ:
```python
from sklearn.metrics import classification_report, f1_score

print(classification_report(y_true, y_pred, zero_division=0))
print("Macro F1:", f1_score(y_true, y_pred, average="macro"))
print("Weighted F1:", f1_score(y_true, y_pred, average="weighted"))
```

Ý nghĩa:
- `macro F1`: coi mọi class quan trọng như nhau
- `weighted F1`: có tính đến số lượng mẫu của từng class

Nếu:
- weighted F1 cao
- macro F1 thấp

thì thường nghĩa là:
- model đang làm tốt trên class lớn
- nhưng làm kém trên class nhỏ

---

## 6. Kỹ thuật nào đang phù hợp nhất cho notebook hiện tại?

Với bài toán text multiclass web attack hiện tại, cách hợp lý cho baseline là:

1. dedup trước split
2. stratified split
3. oversampling trên train split
4. `class_weight='balanced'`
5. đánh giá bằng macro F1 + confusion matrix

Đây chính là hướng đang được dùng vì:
- đơn giản
- sạch notebook
- dễ giải thích
- phù hợp với mô hình baseline như Logistic Regression, Linear SVC

---

## 7. Ví dụ hoàn chỉnh ngắn

```python
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

# 1. stratified split
train_df, test_df = train_test_split(
    data,
    test_size=0.2,
    random_state=42,
    stratify=data["label_multiclass"],
)

# 2. oversampling train split
train_balanced_df = make_balanced_training_frame(train_df)

# 3. model with class_weight
model = Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))),
    ("clf", LogisticRegression(max_iter=1200, class_weight="balanced", random_state=42)),
])

# 4. fit
model.fit(
    train_balanced_df["normalized_text"],
    train_balanced_df["label_multiclass"],
)

# 5. evaluate
pred = model.predict(test_df["normalized_text"])
print(classification_report(test_df["label_multiclass"], pred, zero_division=0))
```

---

## 8. Kết luận

Data imbalance là vấn đề rất thường gặp trong bài toán classification, đặc biệt là security classification và multiclass text classification.

Các ý chính cần nhớ:
- đừng chỉ nhìn accuracy
- luôn kiểm tra phân bố class
- stratified split là bắt buộc gần như trong mọi case
- oversampling và class weights là baseline tốt, dễ áp dụng
- ngay cả khi chỉ có 4 lớp (`Normal`, `SQLi`, `XSS`, `OtherWebAttack`), imbalance vẫn có thể làm model thiên về class lớn

Trong project này, cách xử lý imbalance hiện tại là hợp lý cho một notebook baseline sạch và dễ giải thích. Tuy nhiên, nếu cần kết quả mạnh hơn nữa, có thể mở rộng sang:
- so sánh nhiều chiến lược balancing
- threshold tuning
- augmentation cho payload security
- pipeline đánh giá riêng cho từng class hiếm
