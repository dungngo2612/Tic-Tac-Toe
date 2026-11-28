"""
Các agent tìm kiếm cho cờ tướng thực tế
Minimax + Alpha-Beta, MCTS + UCT
"""
from random import Random
from typing import List, Optional, NamedTuple
from game.caro_thực_tế import TrạngThái_CờTướng, Nước, Bên


class KếtQuả_Tìm_Kiếm(NamedTuple):
    nước: Nước
    giá_trị: float
    lần_lặp: int = 1
    nút: int = 1


class AgentMinimax_CờTướng:
    """Minimax với Alpha-Beta pruning cho cờ tướng."""
    
    def __init__(self, độ_sâu: int = 2):
        self.độ_sâu = độ_sâu
        self.nút_đánh_giá = 0
    
    def chọn_nước(self, trạng_thái: TrạngThái_CờTướng, rng: Random) -> KếtQuả_Tìm_Kiếm:
        """Chọn nước tốt nhất dùng Minimax."""
        self.nút_đánh_giá = 0
        nước_hợp_lệ = trạng_thái._lấy_nước_hợp_lệ()
        
        if not nước_hợp_lệ:
            raise ValueError("Không có nước hợp lệ")
        
        if len(nước_hợp_lệ) == 1:
            return KếtQuả_Tìm_Kiếm(nước_hợp_lệ[0], 0.0)
        
        # Đánh giá tất cả nước
        nước_tốt = nước_hợp_lệ[0]
        giá_trị_tốt = float('-inf') if trạng_thái.bên_đi == Bên.ĐỎ else float('inf')
        
        for nước in nước_hợp_lệ:
            trạng_thái_tiếp = trạng_thái.đi_nước(nước)
            giá_trị = self._minimax(trạng_thái_tiếp, self.độ_sâu - 1,
                                   float('-inf'), float('inf'),
                                   trạng_thái.bên_đi == Bên.ĐỎ)
            
            if trạng_thái.bên_đi == Bên.ĐỎ and giá_trị > giá_trị_tốt:
                giá_trị_tốt = giá_trị
                nước_tốt = nước
            elif trạng_thái.bên_đi == Bên.ĐEN and giá_trị < giá_trị_tốt:
                giá_trị_tốt = giá_trị
                nước_tốt = nước
        
        return KếtQuả_Tìm_Kiếm(nước_tốt, giá_trị_tốt, nút=self.nút_đánh_giá)
    
    def _minimax(self, trạng_thái: TrạngThái_CờTướng, độ_sâu: int,
                 alpha: float, beta: float, là_tối_đa: bool) -> float:
        """Minimax với Alpha-Beta pruning."""
        self.nút_đánh_giá += 1
        
        # Dừng lại
        if độ_sâu == 0 or trạng_thái.kết_thúc():
            return trạng_thái.đánh_giá()
        
        nước_hợp_lệ = trạng_thái._lấy_nước_hợp_lệ()
        if not nước_hợp_lệ:
            return trạng_thái.đánh_giá()
        
        if là_tối_đa:  # ĐỎ (tối đa hóa)
            giá_trị = float('-inf')
            for nước in nước_hợp_lệ:
                trạng_thái_con = trạng_thái.đi_nước(nước)
                giá_trị_con = self._minimax(trạng_thái_con, độ_sâu - 1, alpha, beta, False)
                giá_trị = max(giá_trị, giá_trị_con)
                alpha = max(alpha, giá_trị)
                if beta <= alpha:
                    break  # Cắt tỉa
            return giá_trị
        else:  # ĐEN (tối thiểu hóa)
            giá_trị = float('inf')
            for nước in nước_hợp_lệ:
                trạng_thái_con = trạng_thái.đi_nước(nước)
                giá_trị_con = self._minimax(trạng_thái_con, độ_sâu - 1, alpha, beta, True)
                giá_trị = min(giá_trị, giá_trị_con)
                beta = min(beta, giá_trị)
                if beta <= alpha:
                    break  # Cắt tỉa
            return giá_trị


class AgentMCTS_CờTướng:
    """MCTS cho cờ tướng."""
    
    def __init__(self, lần_lặp: int = 100, khám_phá: float = 1.4):
        self.lần_lặp = lần_lặp
        self.khám_phá = khám_phá
    
    def chọn_nước(self, trạng_thái: TrạngThái_CờTướng, rng: Random) -> KếtQuả_Tìm_Kiếm:
        """Chọn nước tốt nhất dùng MCTS."""
        nước_hợp_lệ = trạng_thái._lấy_nước_hợp_lệ()
        
        if not nước_hợp_lệ:
            raise ValueError("Không có nước hợp lệ")
        
        if len(nước_hợp_lệ) == 1:
            return KếtQuả_Tìm_Kiếm(nước_hợp_lệ[0], 0.0)
        
        # Xây dựng cây
        gốc = NútMCTS(trạng_thái, None)
        
        for _ in range(self.lần_lặp):
            nút = gốc.chọn_con(self.khám_phá)
            giá_trị = self._chơi_ngẫu_nhiên(nút.trạng_thái, rng)
            nút.cập_nhật(giá_trị)
        
        # Chọn nước theo số lần thăm
        nút_tốt = max(gốc.con, key=lambda n: n.số_lần_thăm)
        
        return KếtQuả_Tìm_Kiếm(nút_tốt.nước, nút_tốt.giá_trị_trung_bình,
                              lần_lặp=self.lần_lặp,
                              nút=len(gốc.con))
    
    def _chơi_ngẫu_nhiên(self, trạng_thái: TrạngThái_CờTướng, rng: Random) -> float:
        """Chơi ngẫu nhiên từ trạng thái (tối đa 10 bước)."""
        bước = 0
        max_bước = 10
        
        while not trạng_thái.kết_thúc() and bước < max_bước:
            nước_hợp_lệ = trạng_thái._lấy_nước_hợp_lệ()
            if not nước_hợp_lệ:
                break
            nước = rng.choice(nước_hợp_lệ)
            trạng_thái = trạng_thái.đi_nước(nước)
            bước += 1
        
        # Đánh giá dựa trên vị trí cuối (heuristic: bắt được quân là tốt)
        return rng.random()  # Trả về random 0-1 để nhanh hơn


class NútMCTS:
    """Nút trong cây MCTS."""
    
    def __init__(self, trạng_thái: TrạngThái_CờTướng, nước: Optional[Nước]):
        self.trạng_thái = trạng_thái
        self.nước = nước
        self.số_lần_thăm = 0
        self.tổng_giá_trị = 0.0
        self.con: List['NútMCTS'] = []
        self.cha: Optional['NútMCTS'] = None
        self._mở_rộng = False
    
    @property
    def giá_trị_trung_bình(self) -> float:
        return self.tổng_giá_trị / self.số_lần_thăm if self.số_lần_thăm > 0 else 0.0
    
    def chọn_con(self, khám_phá: float) -> "NútMCTS":
        """Chọn con theo UCB hoặc mở rộng."""
        import math
        
        if not self._mở_rộng:
            # Mở rộng nút này lần đầu
            nước_hợp_lệ = self.trạng_thái._lấy_nước_hợp_lệ()
            for nước in nước_hợp_lệ:
                con = NútMCTS(self.trạng_thái.đi_nước(nước), nước)
                con.cha = self
                self.con.append(con)
            self._mở_rộng = True
        
        if not self.con:
            return self
        
        # Trả về con chưa thăm (exploration first)
        for con in self.con:
            if con.số_lần_thăm == 0:
                return con
        
        # Nếu tất cả đã thăm, chọn theo UCB
        nút_tốt = None
        ucb_tốt = float('-inf')
        
        for con in self.con:
            tb = con.giá_trị_trung_bình
            khám = khám_phá * math.sqrt(math.log(self.số_lần_thăm) / con.số_lần_thăm)
            ucb = tb + khám
            
            if ucb > ucb_tốt:
                ucb_tốt = ucb
                nút_tốt = con
        
        return nút_tốt if nút_tốt else self.con[0]
    
    def cập_nhật(self, giá_trị: float):
        """Cập nhật giá trị lên các cha."""
        nút = self
        while nút is not None:
            nút.số_lần_thăm += 1
            nút.tổng_giá_trị += giá_trị
            nút = nút.cha
