# Hướng dẫn xếp hồ sơ vào các ô upload

Mỗi hồ sơ là một thư mục (`INPUT_PATHS`), bên trong có 7 thư mục con — mỗi thư mục là một
"ô upload". Danh sách loại giấy tờ đầy đủ (và từ khóa nhận diện) nằm ở
[`src/agents/documents/document_matrix.yaml`](../src/agents/documents/document_matrix.yaml) —
muốn thêm loại giấy tờ mới thì sửa ở đó.

| Ô hồ sơ | Để giấy tờ gì |
|---|---|
| **`ho_so_phap_ly`** | GCN ĐKDN (bản mới nhất), điều lệ, sổ cổ đông / sổ thành viên, HĐ chuyển nhượng vốn, quyết định bổ nhiệm, nghị quyết / biên bản họp, quyết định xử phạt, biên bản thanh tra, hồ sơ tranh chấp / tòa án |
| **`ho_so_tai_chinh`** | BCTC năm, thuyết minh BCTC, tờ khai VAT, **hợp đồng đầu ra / đầu vào, hóa đơn VAT, sao kê tài khoản DN**, thông báo nợ thuế, xác nhận BHXH |
| **`ho_so_vay_von`** | Giấy đề nghị cấp tín dụng, phương án vay vốn, **phương án kinh doanh / dự phóng hoạt động kinh doanh** |
| **`ho_so_tai_san_dam_bao`** | Giấy tờ TSBĐ, **chứng thư định giá** |
| **`ho_so_noi_bo`** | Tra cứu Cổng ĐKDN / masothue.com, tra cứu nợ thuế / BHXH, bản in T24 / BCDE / BEP / DBX, **báo cáo CIC** |
| **`ho_so_soan_thao_noi_bo`** | Báo cáo khảo sát thực địa, AI Site Visit, hình ảnh trụ sở / nhà xưởng / biển hiệu, tờ trình |
| **`ho_so_khac`** | Giấy tờ không thuộc các ô trên |

## Lưu ý

- **Hợp đồng đầu ra / đầu vào** vào `ho_so_tai_chinh` (loại "Hợp đồng kinh tế, hóa đơn VAT, sao kê
  tài khoản doanh nghiệp") — chứng từ thể hiện thu chi của doanh nghiệp.
- **Dự phóng hoạt động kinh doanh** vào `ho_so_vay_von`: chỉ loại giấy tờ này được đọc số kế hoạch
  (doanh thu, LNST) cho mục 5 – PAKD. Đặt tên file có chữ **"pakd"** hoặc **"phuong an"**
  (ví dụ `PAKD_2026.pdf`) để được nhận đúng loại ngay.
- **Chứng thư định giá** vào `ho_so_tai_san_dam_bao`.
- **KH cá nhân vay vốn**: để `BORROWER_NAMES = []` thì hệ thống tự tìm tên thành viên góp vốn /
  người đại diện theo pháp luật trong `ho_so_vay_von` (rồi `ho_so_soan_thao_noi_bo`). Vì vậy hồ sơ
  nên có giấy đề nghị vay vốn hoặc tờ trình trong hai ô này. Điền tay `BORROWER_NAMES` thì tên điền
  tay được ưu tiên.
- Để nhầm ô không làm hỏng kết quả: hệ thống đọc nội dung để phân loại lại và báo trong "Steps" file
  nào có nội dung không khớp ô đã để. Nhưng nên để đúng ô, vì một số bước chỉ đọc một ô (ví dụ tự
  tìm KH vay).
