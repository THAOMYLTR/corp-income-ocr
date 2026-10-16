<!--
Phụ lục 01 — template của người dùng, giữ nguyên bố cục. Ghi chú này không vào báo cáo.

Cách điền:
- CODE điền (lấy từ hồ sơ / tính toán, không qua LLM): mục 1.1, bảng 1.2, TSC,
  toàn bộ bảng tài chính và chỉ số (đơn vị: triệu đồng), cột lịch sử của mục 5.
  Danh sách tên: src/utils/report/appendix_context.py.
- LLM viết (theo src/templates/corp-income-guidance.md): các ô còn lại — nhận xét,
  hoạt động kinh doanh, CIC, phương án kinh doanh, kết luận.
- Bổ sung so với bản gốc: NhanXetPhapLyDN ở mục 1.1 và các ô mục 5 (bảng
  phương án kinh doanh gốc để trống).
- [BRD 16/10] Năm tương đối: Nam-1 = năm BCTC gần nhất trong hồ sơ, Nam-2 = năm trước đó;
  ô ghi theo dạng DTTN-1, TongTaiSanN-2, ROSN-1… Năm không có BCTC hiện "—".
-->
## PHỤ LỤC 01 - THẨM ĐỊNH NGUỒN THU DOANH NGHIỆP

### 1. Pháp lý doanh nghiệp

#### 1.1. Thông tin cơ bản về pháp lý doanh nghiệp

| Nội dung | Giá trị |
|----------|----------|
| Tên doanh nghiệp | {{TenDoanhNghiep}} |
| ID T24 (nếu có) | {{T24ID}} |
| Mã số thuế | {{MST}} |
| Năm thành lập | {{NamThanhLap}} |
| Đăng ký kinh doanh lần đầu / thay đổi gần nhất | {{DKKD}} |
| Người đại diện theo pháp luật | {{NguoiDaiDien}} |
| Tình trạng hoạt động | {{TinhTrangHoatDong}} |

_Nhận xét về pháp lý doanh nghiệp:_ {{NhanXetPhapLyDN}}

#### 1.2. Thành viên góp vốn và người đại diện theo pháp luật

| Họ và tên | Mối quan hệ | Tỷ lệ góp vốn | Thay đổi thành viên góp vốn / Người đại diện pháp luật trong 12 tháng gần nhất |
|------------|------------|------------|------------|
| {{ThanhVien1}} | {{MoiQuanHe1}} | {{TyLe1}} | {{ThayDoi1}} |
| {{ThanhVien2}} | {{MoiQuanHe2}} | {{TyLe2}} | {{ThayDoi2}} |
| {{ThanhVien3}} | {{MoiQuanHe3}} | {{TyLe3}} | {{ThayDoi3}} |

_Nhận xét về pháp lý khách hàng:_ {{NhanXet}}

---

### 2. Hoạt động kinh doanh

#### 2.1. Thông tin hoạt động

| Nội dung | Thông tin |
|-----------|-----------|
| Nguồn | {{Nguon}} |
| Sản phẩm / dịch vụ | {{SanPhamDichVu}} |
| Địa chỉ | - TSC: {{TruSoChinh}}<br>- Nhà xưởng: {{NhaXuong}}<br>- Kho hàng: {{KhoHang}} |
| Thông tin chi tiết về HĐKD của Khách hàng (nếu có) | **Đầu ra**<br><br><table><tr><th>Doanh nghiệp</th><th>Giá trị</th><th>Tỷ trọng</th><th>Ghi chú</th></tr><tr><td>{{DoanhNghiepA}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepB}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepC}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepD}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepE}}</td><td></td><td></td><td></td></tr></table><br><br>**Đầu vào**<br><br><table><tr><th>Doanh nghiệp</th><th>Giá trị</th><th>Tỷ trọng</th><th>Ghi chú</th></tr><tr><td>{{DoanhNghiepF}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepG1}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepG2}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepG3}}</td><td></td><td></td><td></td></tr><tr><td>{{DoanhNghiepB}}</td><td></td><td></td><td></td></tr></table> |

_Nhận xét về hoạt động kinh doanh của khách hàng:_ {{NhanXetHDKD}}

---

### 3. Tài chính

| Nguồn | {{NguonTaiChinh}} |
|--------|--------|

#### Tóm tắt tài chính

<table>
<tr>
<th>Bảng cân đối kế toán</th>
<th>31/12/{{Nam-2}}</th>
<th>31/12/{{Nam-1}}</th>
<th>Báo cáo kết quả hoạt động kinh doanh</th>
<th>{{Nam-2}}</th>
<th>{{Nam-1}}</th>
<th>Cập nhật các tháng {{NamHienTai}}</th>
</tr>

<tr>
<td>Tổng tài sản</td>
<td>{{TongTaiSanN-2}}</td>
<td>{{TongTaiSanN-1}}</td>
<td>Doanh thu thuần</td>
<td>{{DTTN-2}}</td>
<td>{{DTTN-1}}</td>
<td>{{DTTCurrent}}</td>
</tr>

<tr>
<td>Tài sản ngắn hạn</td>
<td>{{TSNHN-2}}</td>
<td>{{TSNHN-1}}</td>
<td>Giá vốn hàng bán</td>
<td>{{GVHBN-2}}</td>
<td>{{GVHBN-1}}</td>
<td>{{GVHBCurrent}}</td>
</tr>

<tr>
<td>Tài sản dài hạn</td>
<td>{{TSDHN-2}}</td>
<td>{{TSDHN-1}}</td>
<td>Lợi nhuận gộp</td>
<td>{{LNGN-2}}</td>
<td>{{LNGN-1}}</td>
<td>{{LNGCurrent}}</td>
</tr>

<tr>
<td>Tổng nguồn vốn</td>
<td>{{TongNguonVonN-2}}</td>
<td>{{TongNguonVonN-1}}</td>
<td>Doanh thu tài chính</td>
<td>{{DTTCN-2}}</td>
<td>{{DTTCN-1}}</td>
<td>{{DTTCCurrent}}</td>
</tr>

<tr>
<td>Nợ phải trả</td>
<td>{{NoPhaiTraN-2}}</td>
<td>{{NoPhaiTraN-1}}</td>
<td>Chi phí tài chính</td>
<td>{{CPTCN-2}}</td>
<td>{{CPTCN-1}}</td>
<td>{{CPTCCurrent}}</td>
</tr>

<tr>
<td>Vốn chủ sở hữu</td>
<td>{{VCSHN-2}}</td>
<td>{{VCSHN-1}}</td>
<td>Chi phí quản lý doanh nghiệp</td>
<td>{{CPQLN-2}}</td>
<td>{{CPQLN-1}}</td>
<td>{{CPQLCurrent}}</td>
</tr>

<tr>
<td><b>Các chỉ số tài chính</b></td>
<td></td>
<td></td>
<td>Chi phí bán hàng</td>
<td>{{CPBHN-2}}</td>
<td>{{CPBHN-1}}</td>
<td>{{CPBHCurrent}}</td>
</tr>

<tr>
<td>Biến động doanh thu</td>
<td>{{BienDongDTN-2}}</td>
<td>{{BienDongDTN-1}}</td>
<td>Lợi nhuận thuần</td>
<td>{{LNThuanN-2}}</td>
<td>{{LNThuanN-1}}</td>
<td>{{LNThuanCurrent}}</td>
</tr>

<tr>
<td>LN sau thuế / DTT</td>
<td>{{ROSN-2}}</td>
<td>{{ROSN-1}}</td>
<td>Lợi nhuận trước thuế</td>
<td>{{LNTTN-2}}</td>
<td>{{LNTTN-1}}</td>
<td>{{LNTTCurrent}}</td>
</tr>

<tr>
<td>Hệ số thanh toán hiện hành</td>
<td>{{CurrentRatioN-2}}</td>
<td>{{CurrentRatioN-1}}</td>
<td>Lợi nhuận sau thuế</td>
<td>{{LNSTN-2}}</td>
<td>{{LNSTN-1}}</td>
<td>{{LNSTCurrent}}</td>
</tr>
</table>

### Nhận xét về tài chính khách hàng

{{NhanXetTaiChinh}}

### 4. Dư nợ tại TCTD

#### a. Ngày

{{NgayDuLieuCIC}}

#### b. Số dư cấp tín dụng hiện tại

<table>
<tr>
<th rowspan="2">TCTD</th>
<th colspan="5">Số dư cấp tín dụng</th>
<th rowspan="2">Tổng TSBĐ</th>
<th rowspan="2">Chủ sở hữu TSBĐ</th>
</tr>

<tr>
<th>Dư nợ ngắn hạn</th>
<th>Dư nợ TDH</th>
<th>Dư nợ khác</th>
<th>CKNB</th>
<th>Tổng số dư CTD</th>
</tr>

<tr>
<td>TCB (1)</td>
<td>{{TCB_ST}}</td>
<td>{{TCB_MLT}}</td>
<td>{{TCB_Other}}</td>
<td>{{TCB_CKNB}}</td>
<td>{{TCB_Total}}</td>
<td>{{TCB_Collateral}}</td>
<td>{{TCB_CollateralOwner}}</td>
</tr>

<tr>
<td>TCTD khác (2)</td>
<td>{{OtherBank_ST}}</td>
<td>{{OtherBank_MLT}}</td>
<td>{{OtherBank_Other}}</td>
<td>{{OtherBank_CKNB}}</td>
<td>{{OtherBank_Total}}</td>
<td>{{OtherBank_Collateral}}</td>
<td>{{OtherBank_CollateralOwner}}</td>
</tr>

<tr>
<td><b>Tổng tại các TCTD (1) + (2)</b></td>
<td>{{Total_ST}}</td>
<td>{{Total_MLT}}</td>
<td>{{Total_Other}}</td>
<td>{{Total_CKNB}}</td>
<td>{{Total_Credit}}</td>
<td>{{Total_Collateral}}</td>
<td></td>
</tr>

</table>

#### c. Chất lượng tín dụng

**Chất lượng tín dụng**

{{CreditQuality}}

**Thông tin nợ cần chú ý**

{{SpecialMention}}

**Thông tin nợ xấu**

{{BadDebt}}

### Nhận xét về dư nợ TCTD

{{NhanXetDuNo}}

### 5. Phương án kinh doanh (nếu có)

| Phương án kinh doanh (nếu có) | {{Nam-2}} | {{Nam-1}} | Cập nhật năm T | Năm kế hoạch | Cơ sở của Khách hàng |
|---|---|---|---|---|---|
| Doanh thu thuần | {{DTTN-2}} | {{DTTN-1}} | {{DTTCurrent}} | {{PAKD_DTT_KeHoach}} | {{PAKD_DTT_CoSo}} |
| Tốc độ tăng trưởng DTT | {{BienDongDTN-2}} | {{BienDongDTN-1}} | | {{PAKD_TangTruong_KeHoach}} | {{PAKD_TangTruong_CoSo}} |
| Lợi nhuận sau thuế | {{LNSTN-2}} | {{LNSTN-1}} | {{LNSTCurrent}} | {{PAKD_LNST_KeHoach}} | {{PAKD_LNST_CoSo}} |
| Tỷ lệ LNST/DTT | {{ROSN-2}} | {{ROSN-1}} | | {{PAKD_ROS_KeHoach}} | {{PAKD_ROS_CoSo}} |

**Nhận xét về phương án kinh doanh**

{{NhanXetPAKD}}

---

### 6. Kết luận về nguồn thu doanh nghiệp

{{KetLuanNguonThuDoanhNghiep}}

{{KetLuan}}
