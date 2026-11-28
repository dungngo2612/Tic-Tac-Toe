"""
Cờ tướng thực tế - Luật chơi đầy đủ
Bàn 10×9, 32 quân (vua, tướng, tệ, mã, xe, pháo, binh)
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
from enum import Enum


class LoạiQuân(Enum):
    VUA = "V"      # Vua - di chuyển 1 ô trong cung
    TƯỚNG = "T"    # Tướng - di chuyển 1 ô trong cung
    TỆ = "t"       # Tệ - di chuyển 1 ô theo đường chéo trong cung
    MÃ = "M"       # Mã - di chuyển hình chữ L
    XE = "X"       # Xe - di chuyển thẳng (hàng, cột)
    PHÁO = "P"     # Pháo - di chuyển thẳng, bắt qua quân
    BINH = "B"     # Binh - di chuyển 1 ô, sau sông di chuyển ngang


class Bên(Enum):
    ĐỎ = 1
    ĐEN = -1


@dataclass
class Quân:
    """Một quân cờ trên bàn."""
    bên: Bên
    loại: LoạiQuân
    
    def __repr__(self):
        tiền_tố = "Đ" if self.bên == Bên.ĐỎ else "Đ"
        return f"{tiền_tố}{self.loại.value}"


@dataclass
class Nước:
    """Một nước đi: (từ_hàng, từ_cột) -> (đến_hàng, đến_cột)"""
    từ_vị_trí: Tuple[int, int]
    đến_vị_trí: Tuple[int, int]
    
    def __repr__(self):
        h1, c1 = self.từ_vị_trí
        h2, c2 = self.đến_vị_trí
        return f"({h1},{c1})->({h2},{c2})"


class TrạngThái_CờTướng:
    """
    Trạng thái cờ tướng:
    - Bàn: 10×9 (10 hàng, 9 cột)
    - Hàng 0-2: Cung đỏ (3 hàng)
    - Hàng 6-8: Cung đen (3 hàng)
    - Hàng 3-5: Sông (3 hàng)
    - Cột 3-5: Cung (3 cột)
    """
    
    SỐ_HÀNG = 10
    SỐ_CỘT = 9
    
    def __init__(self, bàn: Optional[dict] = None, bên_đi: Bên = Bên.ĐỎ):
        """
        bàn: dict {(hàng, cột): Quân}
        bên_đi: Bên.ĐỎ hoặc Bên.ĐEN
        """
        if bàn is None:
            self.bàn = self._khởi_tạo_bàn()
        else:
            self.bàn = bàn.copy()
        
        self.bên_đi = bên_đi
        self.lịch_sử_nước = []
    
    def _khởi_tạo_bàn(self) -> dict:
        """Khởi tạo vị trí ban đầu."""
        bàn = {}
        
        # === ĐỎ (hàng 0-2) ===
        # Vua: (1, 4)
        bàn[(1, 4)] = Quân(Bên.ĐỎ, LoạiQuân.VUA)
        # Tướng: (0, 3), (0, 5)
        bàn[(0, 3)] = Quân(Bên.ĐỎ, LoạiQuân.TƯỚNG)
        bàn[(0, 5)] = Quân(Bên.ĐỎ, LoạiQuân.TƯỚNG)
        # Tệ: (2, 3), (2, 5)
        bàn[(2, 3)] = Quân(Bên.ĐỎ, LoạiQuân.TỆ)
        bàn[(2, 5)] = Quân(Bên.ĐỎ, LoạiQuân.TỆ)
        # Mã: (0, 1), (0, 7)
        bàn[(0, 1)] = Quân(Bên.ĐỎ, LoạiQuân.MÃ)
        bàn[(0, 7)] = Quân(Bên.ĐỎ, LoạiQuân.MÃ)
        # Xe: (0, 0), (0, 8)
        bàn[(0, 0)] = Quân(Bên.ĐỎ, LoạiQuân.XE)
        bàn[(0, 8)] = Quân(Bên.ĐỎ, LoạiQuân.XE)
        # Pháo: (2, 1), (2, 7)
        bàn[(2, 1)] = Quân(Bên.ĐỎ, LoạiQuân.PHÁO)
        bàn[(2, 7)] = Quân(Bên.ĐỎ, LoạiQuân.PHÁO)
        # Binh: (3, 0), (3, 2), (3, 4), (3, 6), (3, 8)
        for cột in [0, 2, 4, 6, 8]:
            bàn[(3, cột)] = Quân(Bên.ĐỎ, LoạiQuân.BINH)
        
        # === ĐEN (hàng 6-8) ===
        # Vua: (8, 4)
        bàn[(8, 4)] = Quân(Bên.ĐEN, LoạiQuân.VUA)
        # Tướng: (9, 3), (9, 5)
        bàn[(9, 3)] = Quân(Bên.ĐEN, LoạiQuân.TƯỚNG)
        bàn[(9, 5)] = Quân(Bên.ĐEN, LoạiQuân.TƯỚNG)
        # Tệ: (7, 3), (7, 5)
        bàn[(7, 3)] = Quân(Bên.ĐEN, LoạiQuân.TỆ)
        bàn[(7, 5)] = Quân(Bên.ĐEN, LoạiQuân.TỆ)
        # Mã: (9, 1), (9, 7)
        bàn[(9, 1)] = Quân(Bên.ĐEN, LoạiQuân.MÃ)
        bàn[(9, 7)] = Quân(Bên.ĐEN, LoạiQuân.MÃ)
        # Xe: (9, 0), (9, 8)
        bàn[(9, 0)] = Quân(Bên.ĐEN, LoạiQuân.XE)
        bàn[(9, 8)] = Quân(Bên.ĐEN, LoạiQuân.XE)
        # Pháo: (7, 1), (7, 7)
        bàn[(7, 1)] = Quân(Bên.ĐEN, LoạiQuân.PHÁO)
        bàn[(7, 7)] = Quân(Bên.ĐEN, LoạiQuân.PHÁO)
        # Binh: (6, 0), (6, 2), (6, 4), (6, 6), (6, 8)
        for cột in [0, 2, 4, 6, 8]:
            bàn[(6, cột)] = Quân(Bên.ĐEN, LoạiQuân.BINH)
        
        return bàn
    
    def _trong_cung(self, hàng: int, cột: int, bên: Bên) -> bool:
        """Kiểm tra vị trí có trong cung không."""
        if bên == Bên.ĐỎ:
            return 0 <= hàng <= 2 and 3 <= cột <= 5
        else:
            return 6 <= hàng <= 9 and 3 <= cột <= 5
    
    def _mã_có_thể_đi(self, từ_h: int, từ_c: int, đến_h: int, đến_c: int) -> bool:
        """Kiểm tra mã có thể đi không (hình chữ L + không bị chặn)."""
        dh = abs(đến_h - từ_h)
        dc = abs(đến_c - từ_c)
        
        if not ((dh == 2 and dc == 1) or (dh == 1 and dc == 2)):
            return False
        
        # Kiểm tra quân chặn đường
        if dh == 2:  # Di chuyển theo hàng
            chặn_h = từ_h + (1 if đến_h > từ_h else -1)
            chặn_c = từ_c
        else:  # Di chuyển theo cột
            chặn_h = từ_h
            chặn_c = từ_c + (1 if đến_c > từ_c else -1)
        
        return (chặn_h, chặn_c) not in self.bàn
    
    def _pháo_có_thể_bắt(self, từ_h: int, từ_c: int, đến_h: int, đến_c: int) -> bool:
        """Kiểm tra pháo có thể bắt quân đích (phải có 1 quân chặn)."""
        if từ_h != đến_h and từ_c != đến_c:
            return False  # Pháo chỉ đi thẳng
        
        # Đếm quân trên đường
        quân_trên_đường = 0
        
        if từ_h == đến_h:  # Cùng hàng
            c_min, c_max = min(từ_c, đến_c), max(từ_c, đến_c)
            for c in range(c_min + 1, c_max):
                if (từ_h, c) in self.bàn:
                    quân_trên_đường += 1
        else:  # Cùng cột
            h_min, h_max = min(từ_h, đến_h), max(từ_h, đến_h)
            for h in range(h_min + 1, h_max):
                if (h, từ_c) in self.bàn:
                    quân_trên_đường += 1
        
        return quân_trên_đường == 1  # Phải có đúng 1 quân
    
    def _lấy_nước_hợp_lệ(self) -> List[Nước]:
        """Sinh tất cả nước hợp lệ cho bên đi."""
        nước_hợp_lệ = []
        
        for (h, c), quân in self.bàn.items():
            if quân.bên != self.bên_đi:
                continue
            
            if quân.loại == LoạiQuân.VUA:
                # Vua: di chuyển 1 ô trong cung
                for dh in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dh == 0 and dc == 0:
                            continue
                        nh, nc = h + dh, c + dc
                        if self._trong_cung(nh, nc, quân.bên):
                            nước_hợp_lệ.append(Nước((h, c), (nh, nc)))
            
            elif quân.loại == LoạiQuân.TƯỚNG:
                # Tướng: di chuyển 1 ô trong cung
                for dh in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dh == 0 and dc == 0:
                            continue
                        nh, nc = h + dh, c + dc
                        if self._trong_cung(nh, nc, quân.bên):
                            nước_hợp_lệ.append(Nước((h, c), (nh, nc)))
            
            elif quân.loại == LoạiQuân.TỆ:
                # Tệ: di chuyển theo đường chéo 1 ô trong cung
                for dh, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    nh, nc = h + dh, c + dc
                    if self._trong_cung(nh, nc, quân.bên):
                        nước_hợp_lệ.append(Nước((h, c), (nh, nc)))
            
            elif quân.loại == LoạiQuân.XE:
                # Xe: di chuyển thẳng (hàng, cột) - không được qua quân
                # Hàng
                for nh in range(self.SỐ_HÀNG):
                    if nh == h:
                        continue
                    # Kiểm tra xem có quân chặn không
                    h_min, h_max = min(h, nh), max(h, nh)
                    bị_chặn = any((nh2, c) in self.bàn for nh2 in range(h_min + 1, h_max))
                    if not bị_chặn:
                        nước_hợp_lệ.append(Nước((h, c), (nh, c)))
                # Cột
                for nc in range(self.SỐ_CỘT):
                    if nc == c:
                        continue
                    # Kiểm tra xem có quân chặn không
                    c_min, c_max = min(c, nc), max(c, nc)
                    bị_chặn = any((h, nc2) in self.bàn for nc2 in range(c_min + 1, c_max))
                    if not bị_chặn:
                        nước_hợp_lệ.append(Nước((h, c), (h, nc)))
            
            elif quân.loại == LoạiQuân.MÃ:
                # Mã: hình chữ L (2-1 hoặc 1-2)
                for nh, nc in [(h-2, c-1), (h-2, c+1), (h-1, c-2), (h-1, c+2),
                               (h+1, c-2), (h+1, c+2), (h+2, c-1), (h+2, c+1)]:
                    if 0 <= nh < self.SỐ_HÀNG and 0 <= nc < self.SỐ_CỘT:
                        if self._mã_có_thể_đi(h, c, nh, nc):
                            nước_hợp_lệ.append(Nước((h, c), (nh, nc)))
            
            elif quân.loại == LoạiQuân.PHÁO:
                # Pháo: di chuyển thẳng (hàng, cột)
                # Nước đi thường (không bắt) - không có quân chặn
                for nh in range(self.SỐ_HÀNG):
                    if nh == h or (nh, c) in self.bàn:
                        continue
                    h_min, h_max = min(h, nh), max(h, nh)
                    bị_chặn = any((nh2, c) in self.bàn for nh2 in range(h_min + 1, h_max))
                    if not bị_chặn:
                        nước_hợp_lệ.append(Nước((h, c), (nh, c)))
                
                for nc in range(self.SỐ_CỘT):
                    if nc == c or (h, nc) in self.bàn:
                        continue
                    c_min, c_max = min(c, nc), max(c, nc)
                    bị_chặn = any((h, nc2) in self.bàn for nc2 in range(c_min + 1, c_max))
                    if not bị_chặn:
                        nước_hợp_lệ.append(Nước((h, c), (h, nc)))
                
                # Nước bắt (phải có đúng 1 quân chặn)
                for nh in range(self.SỐ_HÀNG):
                    if nh == h or (nh, c) not in self.bàn:
                        continue
                    if self.bàn[(nh, c)].bên != quân.bên and self._pháo_có_thể_bắt(h, c, nh, c):
                        nước_hợp_lệ.append(Nước((h, c), (nh, c)))
                
                for nc in range(self.SỐ_CỘT):
                    if nc == c or (h, nc) not in self.bàn:
                        continue
                    if self.bàn[(h, nc)].bên != quân.bên and self._pháo_có_thể_bắt(h, c, h, nc):
                        nước_hợp_lệ.append(Nước((h, c), (h, nc)))
            
            elif quân.loại == LoạiQuân.BINH:
                # Binh: di chuyển 1 ô, sau sông di chuyển thêm ngang
                ở_sông = not (3 <= h <= 5 if quân.bên == Bên.ĐỎ else 3 <= h <= 5)
                
                # Di chuyển về phía đối thủ
                dh = -1 if quân.bên == Bên.ĐỎ else 1
                nh, nc = h + dh, c
                if 0 <= nh < self.SỐ_HÀNG:
                    nước_hợp_lệ.append(Nước((h, c), (nh, nc)))
                
                # Nếu đã qua sông, có thể đi ngang
                if ở_sông:
                    for dc in [-1, 1]:
                        nh, nc = h, c + dc
                        if 0 <= nh < self.SỐ_HÀNG and 0 <= nc < self.SỐ_CỘT:
                            nước_hợp_lệ.append(Nước((h, c), (nh, nc)))
        
        # Lọc nước: không thể bắt quân cùng bên
        nước_cuối = []
        for nước in nước_hợp_lệ:
            đến_h, đến_c = nước.đến_vị_trí
            if đến_h < 0 or đến_h >= self.SỐ_HÀNG or đến_c < 0 or đến_c >= self.SỐ_CỘT:
                continue
            nếu_có = self.bàn.get((đến_h, đến_c))
            if nếu_có and nếu_có.bên == self.bên_đi:
                continue
            nước_cuối.append(nước)
        
        return nước_cuối
    
    def đi_nước(self, nước: Nước) -> "TrạngThái_CờTướng":
        """Thực hiện nước đi, trả về trạng thái mới."""
        bàn_mới = self.bàn.copy()
        
        # Bắt quân (nếu có)
        bàn_mới.pop(nước.đến_vị_trí, None)
        
        # Di chuyển
        quân = bàn_mới.pop(nước.từ_vị_trí)
        bàn_mới[nước.đến_vị_trí] = quân
        
        # Tạo trạng thái mới
        trạng_thái_mới = TrạngThái_CờTướng(bàn_mới, Bên.ĐEN if self.bên_đi == Bên.ĐỎ else Bên.ĐỎ)
        trạng_thái_mới.lịch_sử_nước = self.lịch_sử_nước + [nước]
        
        return trạng_thái_mới
    
    def kết_thúc(self) -> bool:
        """Kiểm tra trò chơi có kết thúc không."""
        # Kiểm tra xem có vua không
        bên_đỏ_có_vua = any(p.loại == LoạiQuân.VUA for p in self.bàn.values() if p.bên == Bên.ĐỎ)
        bên_đen_có_vua = any(p.loại == LoạiQuân.VUA for p in self.bàn.values() if p.bên == Bên.ĐEN)
        
        return not (bên_đỏ_có_vua and bên_đen_có_vua)
    
    def lấy_người_thắng(self) -> Optional[Bên]:
        """Lấy người thắng (nếu trò chơi kết thúc)."""
        if not self.kết_thúc():
            return None
        
        bên_đỏ_có_vua = any(p.loại == LoạiQuân.VUA for p in self.bàn.values() if p.bên == Bên.ĐỎ)
        bên_đen_có_vua = any(p.loại == LoạiQuân.VUA for p in self.bàn.values() if p.bên == Bên.ĐEN)
        
        if bên_đỏ_có_vua and not bên_đen_có_vua:
            return Bên.ĐỎ
        elif bên_đen_có_vua and not bên_đỏ_có_vua:
            return Bên.ĐEN
        else:
            return None
    
    def đánh_giá(self) -> float:
        """
        Đánh giá trạng thái.
        ĐỎ (tối đa hóa): dương
        ĐEN (tối thiểu hóa): âm
        """
        # Kiểm tra kết thúc
        người_thắng = self.lấy_người_thắng()
        if người_thắng == Bên.ĐỎ:
            return 10000.0
        elif người_thắng == Bên.ĐEN:
            return -10000.0
        
        # Giá trị quân
        giá_trị_quân = {
            LoạiQuân.VUA: 500,
            LoạiQuân.TƯỚNG: 100,
            LoạiQuân.TỆ: 50,
            LoạiQuân.XE: 400,
            LoạiQuân.MÃ: 300,
            LoạiQuân.PHÁO: 300,
            LoạiQuân.BINH: 100
        }
        
        điểm = 0.0
        for quân in self.bàn.values():
            giá = giá_trị_quân[quân.loại]
            if quân.bên == Bên.ĐỎ:
                điểm += giá
            else:
                điểm -= giá
        
        return điểm
    
    def chuỗi_bàn(self) -> str:
        """In ASCII bàn."""
        lines = ["    " + " ".join(f"{i:2d}" for i in range(self.SỐ_CỘT))]
        
        for h in range(self.SỐ_HÀNG):
            line = f"{h:2d} "
            for c in range(self.SỐ_CỘT):
                quân = self.bàn.get((h, c))
                if quân:
                    tiền_tố = "Đ" if quân.bên == Bên.ĐỎ else "Đ"
                    line += f"{tiền_tố}{quân.loại.value:1s} "
                else:
                    line += " .  "
            lines.append(line)
        
        return "\n".join(lines)
    
    def __repr__(self):
        return self.chuỗi_bàn()
