"""
Giao diện console cho cờ tướng thực tế
Hiển thị bàn cờ 10×9 với 32 quân
"""
from typing import Optional
from game.caro_thực_tế import TrạngThái_CờTướng, Bên, Nước


class GiaoDiện_CờTướng:
    """Giao diện console cho cờ tướng."""
    
    # Ký hiệu quân
    KÝ_HIỆU = {
        'V': '🤴',   # Vua
        'T': '👑',   # Tướng
        't': '🕵️',   # Tệ
        'M': '🐴',   # Mã
        'X': '🚂',   # Xe
        'P': '💣',   # Pháo
        'B': '👤',   # Binh
        '.': '·',    # Trống
    }
    
    @staticmethod
    def hiển_thị_bàn_cờ(trạng_thái: TrạngThái_CờTướng):
        """Hiển thị bàn cờ hiện tại."""
        print("\n" + "="*50)
        print("        BÀN CỜ TƯỚNG THỰC TẾ (10×9)")
        print("="*50 + "\n")
        
        # Hiển thị tọa độ cột
        print("     ", end="")
        for col in range(TrạngThái_CờTướng.SỐ_CỘT):
            print(f"{col:2d}", end=" ")
        print()
        
        # Hiển thị các hàng
        for hàng in range(TrạngThái_CờTướng.SỐ_HÀNG):
            # Thêm chú thích vùng
            if hàng == 0:
                print(f"{hàng:2d} ", end="")
            elif hàng == 3:
                print(f"{hàng:2d}*", end="")  # * cho dòng sông
            elif hàng == 6:
                print(f"{hàng:2d}*", end="")  # * cho dòng sông
            elif hàng == 9:
                print(f"{hàng:2d} ", end="")
            else:
                print(f"{hàng:2d} ", end="")
            
            for col in range(TrạngThái_CờTướng.SỐ_CỘT):
                quân = trạng_thái.bàn.get((hàng, col))
                if quân is None:
                    ký_hiệu = "·"
                else:
                    # In hoa = ĐỎ, thường = ĐEN
                    if quân.bên == Bên.ĐỎ:
                        ký_hiệu = quân.loại.value.upper()
                    else:
                        ký_hiệu = quân.loại.value.lower()
                print(f" {ký_hiệu}", end="")
            
            # Chú thích
            if hàng == 1:
                print("  <- Vua ĐỎ", end="")
            elif hàng == 8:
                print("  <- Vua ĐEN", end="")
            elif hàng in [3, 6]:
                print("  <- SÔNG", end="")
            
            print()
        
        print("\n" + "="*50)
        print("ĐỎ: Chữ in hoa | ĐEN: Chữ thường")
        print("="*50 + "\n")
    
    @staticmethod
    def hiển_thị_thông_tin_trò_chơi(trạng_thái: TrạngThái_CờTướng):
        """Hiển thị thông tin trò chơi."""
        bên_hiện_tại = "ĐỎ" if trạng_thái.bên_đi == Bên.ĐỎ else "ĐEN"
        print(f"[*] Lượt chơi: {bên_hiện_tại}")
        print(f"[*] Số nước đã đi: {len(trạng_thái.lịch_sử_nước)}")
        
        if trạng_thái.kết_thúc():
            người_thắng = trạng_thái.lấy_người_thắng()
            if người_thắng == Bên.ĐỎ:
                print("[OK] ĐỎ thắng!")
            elif người_thắng == Bên.ĐEN:
                print("[OK] ĐEN thắng!")
            else:
                print("[--] Hòa!")
        print()
    
    @staticmethod
    def hiển_thị_lịch_sử(trạng_thái: TrạngThái_CờTướng):
        """Hiển thị lịch sử các nước đã chơi."""
        if not trạng_thái.lịch_sử_nước:
            print("[*] Chưa có nước nào được chơi.\n")
            return
        
        print("[*] Lịch sử nước chơi:")
        for i, nước in enumerate(trạng_thái.lịch_sử_nước, 1):
            bên = "ĐỎ" if i % 2 == 1 else "ĐEN"
            h1, c1 = nước.từ_vị_trí
            h2, c2 = nước.đến_vị_trí
            print(f"  {i}. {bên} đi: ({h1},{c1}) -> ({h2},{c2})")
        print()
    
    @staticmethod
    def nhập_nước(trạng_thái: TrạngThái_CờTướng) -> Optional[Nước]:
        """Nhập nước từ người chơi."""
        print("[?] Định dạng: 'h1 c1 h2 c2' hoặc 'q' để thoát")
        
        while True:
            try:
                nhập = input("    Nhập nước: ").strip()
                if nhập.lower() == 'q':
                    return None
                
                # Parse: h1 c1 h2 c2
                parts = nhập.split()
                if len(parts) != 4:
                    print("    [!] Vui lòng nhập 4 số: h1 c1 h2 c2")
                    continue
                
                h1, c1, h2, c2 = map(int, parts)
                
                # Kiểm tra bounds
                if not (0 <= h1 < TrạngThái_CờTướng.SỐ_HÀNG and 
                        0 <= c1 < TrạngThái_CờTướng.SỐ_CỘT and
                        0 <= h2 < TrạngThái_CờTướng.SỐ_HÀNG and
                        0 <= c2 < TrạngThái_CờTướng.SỐ_CỘT):
                    print("    [!] Tọa độ ngoài bàn cờ!")
                    continue
                
                # Kiểm tra có quân tại vị trí từ
                if (h1, c1) not in trạng_thái.bàn:
                    print("    [!] Không có quân tại vị trí bắt đầu!")
                    continue
                
                # Kiểm tra quân thuộc bên hiện tại
                quân = trạng_thái.bàn[(h1, c1)]
                if quân.bên != trạng_thái.bên_đi:
                    print("    [!] Quân này không phải của bạn!")
                    continue
                
                nước = Nước((h1, c1), (h2, c2))
                
                # Kiểm tra nước hợp lệ
                nước_hợp_lệ = trạng_thái._lấy_nước_hợp_lệ()
                if nước not in nước_hợp_lệ:
                    print("    [!] Nước này không hợp lệ!")
                    continue
                
                return nước
            
            except ValueError:
                print("    [!] Vui lòng nhập số hoặc 'q'")
    
    @staticmethod
    def hiển_thị_thống_kê(thống_kê: dict):
        """Hiển thị thống kê trò chơi."""
        print("\n" + "="*50)
        print("              THỐNG KÊ TRÒ CHƠI")
        print("="*50 + "\n")
        
        for khóa, giá_trị in thống_kê.items():
            print(f"  {khóa}: {giá_trị}")
        print()


class GiaoDiện_So_Sánh_Agent:
    """Giao diện so sánh hai agent."""
    
    @staticmethod
    def hiển_thị_nước_agent(agent_name: str, nước, giá_trị: float, lần_lặp: int = 0):
        """Hiển thị nước của agent."""
        h1, c1 = nước.từ_vị_trí
        h2, c2 = nước.đến_vị_trí
        print(f"[{agent_name}] Chọn: ({h1},{c1}) -> ({h2},{c2})")
        if lần_lặp > 0:
            print(f"      Giá trị: {giá_trị:.3f} (lần lặp: {lần_lặp})")
        else:
            print(f"      Giá trị: {giá_trị:.3f}")
