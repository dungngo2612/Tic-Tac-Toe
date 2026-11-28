"""Test chạy cờ tướng - AI vs AI"""
import sys
from random import Random
from game.caro_thực_tế import TrạngThái_CờTướng, Bên
from ai.caro_agents_thực_tế import AgentMCTS_CờTướng, AgentMinimax_CờTướng


def test_ai_vs_ai():
    """Test chơi AI vs AI."""
    print("\n" + "="*50)
    print("TEST: MCTS vs MCTS - với seed")
    print("="*50 + "\n")
    
    # Tạo agents - cả hai MCTS với lần lặp khác nhau
    agent_mcts1 = AgentMCTS_CờTướng(lần_lặp=5)  # 5 lần lặp
    agent_mcts2 = AgentMCTS_CờTướng(lần_lặp=5)  # 5 lần lặp
    
    # Tạo bàn cờ
    trạng_thái = TrạngThái_CờTướng()
    rng = Random(42)  # Fixed seed cho reproducibility
    
    nước_số = 0
    max_nước = 5  # Chỉ chơi 5 nước để test nhanh
    
    while not trạng_thái.kết_thúc() and nước_số < max_nước:
        nước_số += 1
        
        # Hiển thị bàn cờ
        print(f"\n--- NUOC {nước_số} ---")
        in_bàn_cờ(trạng_thái)
        
        try:
            if trạng_thái.bên_đi == Bên.ĐỎ:
                print("MCTS1 (DO) dang suy nghi...")
                kết_quả = agent_mcts1.chọn_nước(trạng_thái, rng)
                nước = kết_quả.nước
                print(f"MCTS1 chon: ({nước.từ_vị_trí} -> {nước.đến_vị_trí})")
                print(f"  - Gia tri: {kết_quả.giá_trị:.2f}")
            else:
                print("MCTS2 (DEN) dang suy nghi...")
                kết_quả = agent_mcts2.chọn_nước(trạng_thái, rng)
                nước = kết_quả.nước
                print(f"MCTS2 chon: ({nước.từ_vị_trí} -> {nước.đến_vị_trí})")
                print(f"  - Gia tri: {kết_quả.giá_trị:.2f}")
            
            trạng_thái = trạng_thái.đi_nước(nước)
        except Exception as e:
            print(f"[ERR] {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Kết thúc
    print(f"\n--- KET QUA ---")
    in_bàn_cờ(trạng_thái)
    
    người_thắng = trạng_thái.lấy_người_thắng()
    if người_thắng == Bên.ĐỎ:
        print("[OK] MCTS1 (DO) thang!")
    elif người_thắng == Bên.ĐEN:
        print("[OK] MCTS2 (DEN) thang!")
    else:
        print("[--] Hoa!")
    
    print(f"\nTong nuoc: {nước_số}")


def in_bàn_cờ(trạng_thái: TrạngThái_CờTướng):
    """In bàn cờ."""
    # Hiển thị tọa độ cột
    print("     ", end="")
    for col in range(trạng_thái.SỐ_CỘT):
        print(f"{col:2d}", end=" ")
    print()
    
    # Hiển thị các hàng
    for hàng in range(trạng_thái.SỐ_HÀNG):
        print(f"{hàng:2d}  ", end="")
        for col in range(trạng_thái.SỐ_CỘT):
            quân = trạng_thái.bàn.get((hàng, col))
            if quân:
                if quân.bên == Bên.ĐỎ:
                    print(" o", end=" ")  # Red
                else:
                    print(" x", end=" ")  # Black
            else:
                print(" .", end=" ")  # Empty
        print()
    print()


if __name__ == "__main__":
    test_ai_vs_ai()
