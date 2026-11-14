"""9:16 封面：复用片中品牌镜头（园徽 + 拙政观景 + 首页卡片）定格帧，去掉进度条和闪白。
用法: python3 promo/cover.py
"""
import compose

OUT = compose.V / "cover" / "cover-9x16.png"

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    s_brand = next(fn for key, *_rest, fn in compose.SHOT_FNS if key == "brand")
    s_brand(3.0, 3.5).convert("RGB").save(OUT)  # 品牌镜头 3s 处：所有元素已就位
    print(OUT)
