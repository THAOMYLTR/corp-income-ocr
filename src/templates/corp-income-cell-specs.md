<!--
Khung viết cho từng ô do LLM viết (report writer). Sửa file này để đổi cách viết,
không cần sửa code.

Cách dùng: mỗi ô là một mục "## TenO" (đúng tên biến trong template, không có {{ }}).
Nội dung bên dưới là khung LLM PHẢI theo — thứ tự các phần, số câu, cách mở đầu.
Ô không có mục ở đây thì LLM viết theo quy tắc chung (config/prompts/report_writer.md).
Ghi chú trong khối này không gửi cho LLM.
-->

## NhanXetPhapLyDN
Viết đúng khung (mỗi phần một dòng, bỏ phần không có nội dung):
**Kết luận:** <Phù hợp / Cần làm rõ / Rủi ro cao> — 1 câu tóm tắt tình trạng pháp lý của DN.
**Căn cứ:** 2–3 gạch đầu dòng: MST, năm thành lập, NĐDPL, tình trạng — mỗi dòng ghi nguồn đã đối chiếu.
**Cảnh báo:** mỗi cảnh báo pháp lý một gạch đầu dòng, giữ nguyên số liệu, ngày, tên.
**Đề xuất:** việc cần làm tiếp (tra cứu masothue.com, bổ sung hồ sơ…), nếu có.
**Ảnh hưởng tới quyết định:** 1 câu lấy từ "danh_gia_tin_dung.anh_huong_theo_muc.phap_ly" — làm quyết định mạnh lên hay yếu đi, vì sao.

## NhanXet
Viết đúng khung:
**Kết luận:** 1 câu về pháp lý của KH vay đối với DN (sở hữu bao nhiêu %, có là NĐDPL không).
**Căn cứ:** số năm DN hoạt động; % vốn góp KH vay nắm giữ; vai trò NĐDPL — mỗi ý một gạch đầu dòng, có nguồn.
**Cảnh báo pháp lý cần đánh giá lại:** liệt kê nguyên văn các cảnh báo (tên/TSC/NĐDPL/năm thành lập không khớp, DN không hoạt động/tạm ngưng, tổng tỷ lệ sở hữu ≠ 100%, thay đổi thành viên/NĐDPL trong 12 tháng).
**Ảnh hưởng tới quyết định:** 1 câu lấy từ "danh_gia_tin_dung.anh_huong_theo_muc.phap_ly" — làm quyết định mạnh lên hay yếu đi, vì sao.

## SanPhamDichVu
Đúng 3 dòng nối bằng "<br>":
Loại hình: <sản xuất / thương mại / dịch vụ> (<tỷ trọng nếu đa loại hình>) — <nguồn>
Tên ngành: <tên theo bảng ngành TCB, hoặc như hồ sơ + "chưa đối chiếu bảng ngành TCB">
Diễn giải chi tiết: <sản phẩm chính, quy mô, theo báo cáo thực địa — hoặc "Báo cáo thực địa chưa có thông tin">

## NhanXetHDKD
Viết đúng khung:
**Kết luận:** <Phù hợp / Cần làm rõ / Rủi ro cao> — 1 câu: DN làm gì, ở đâu, đã xác minh qua tài liệu nào.
**Đối chiếu:** 2–4 gạch đầu dòng, mỗi dòng: <nguồn A> vs <nguồn B> → khớp / không khớp (ngành nghề, sản phẩm, địa chỉ, đối tác).
**Cảnh báo:** các cảnh báo của mục 2 trong guidance (thiếu loại hình/ngành nghề, ảnh thiếu biển hiệu, sản phẩm/địa chỉ không khớp…).
**Đề xuất:** tài liệu cần bổ sung (hợp đồng đầu ra/đầu vào, hóa đơn, sổ TK 131/331, hợp đồng thuê…).
**Ảnh hưởng tới quyết định:** 1 câu lấy từ "danh_gia_tin_dung.anh_huong_theo_muc.hoat_dong_kinh_doanh" — làm quyết định mạnh lên hay yếu đi, vì sao.

## NhanXetTaiChinh
Giữ NGUYÊN mọi con số, tỷ lệ, năm trong bản nháp của hệ thống. Viết đúng khung:
**Kết luận:** <Tài chính ổn định / Có dấu hiệu suy giảm / BCTC có mâu thuẫn trọng yếu> — 1 câu.
**Cảnh báo dấu hiệu bất thường của BCTC:** gạch đầu dòng, nguyên văn số liệu.
**Trạng thái tài chính:** phân khúc; biến động doanh thu; hiệu quả (ROS, chất lượng lợi nhuận, lãi vay); thanh khoản — mỗi ý một dòng, có số.
**Doanh thu năm hiện tại:** theo tờ khai VAT (nếu có).
Dòng "Phân nhóm tài chính (POC)" giữ nguyên ở cuối nếu bản nháp có.
**Ảnh hưởng tới quyết định:** 1 câu lấy từ "danh_gia_tin_dung.anh_huong_theo_muc.tai_chinh" — làm quyết định mạnh lên hay yếu đi, vì sao.

## NhanXetDuNo
Giữ NGUYÊN mọi con số trong bản nháp. Viết đúng khung:
**Kết luận:** 1 câu về lịch sử tín dụng (tốt / có nợ cần chú ý / có nợ xấu / chưa có CIC).
**Căn cứ:** ngày bản tin CIC; tổng dư nợ, tại TCB / TCTD khác; dư nợ BQ 12 tháng / doanh thu BQ tháng so với ngưỡng.
**Cảnh báo:** bản tin quá hạn, thiếu R20, chi phí lãi vay không tương quan dư nợ…
Dòng "Phân nhóm bureau (POC)" giữ nguyên ở cuối nếu bản nháp có.
**Ảnh hưởng tới quyết định:** 1 câu lấy từ "danh_gia_tin_dung.anh_huong_theo_muc.tin_dung" — làm quyết định mạnh lên hay yếu đi, vì sao.

## NhanXetPAKD
Viết đúng khung:
**Kết luận:** 1 câu: phương án có / không có cơ sở so với lịch sử và thực địa.
**So sánh:** doanh thu, LNST kế hoạch vs năm gần nhất (dùng số trong bảng, nêu tăng trưởng).
**Cảnh báo:** tăng mạnh không có cơ sở; mâu thuẫn với thực địa hoặc kết quả kinh doanh lịch sử.
**Ảnh hưởng tới quyết định:** 1 câu lấy từ "danh_gia_tin_dung.anh_huong_theo_muc.phuong_an_kinh_doanh" — làm quyết định mạnh lên hay yếu đi, vì sao.

## KetLuanNguonThuDoanhNghiep
Viết đúng khung, theo "danh_gia_tin_dung" (quyết định đã chốt, KHÔNG đổi):
**Đề xuất: <Sử dụng / Sử dụng có điều kiện / Không sử dụng> nguồn thu doanh nghiệp để đánh giá năng lực trả nợ lần này.**
**Lý do chính:** 2–3 gạch đầu dòng mạnh nhất (rủi ro hoặc điểm mạnh), mỗi dòng có số liệu + nguồn.
**Rủi ro còn lại & biện pháp giảm thiểu:** chỉ rủi ro mức cao / trung bình.
**Điều kiện:** (khi "Sử dụng có điều kiện") điều kiện trước giải ngân / trong thời gian vay.
**Hồ sơ cần bổ sung / câu hỏi cho ĐVKD:** gạch đầu dòng cụ thể.
Không nhắc lại công thức / giá trị thu nhập — hệ thống in ngay bên dưới.
