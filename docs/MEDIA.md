# 展示媒体与源码边界

## 正式产品

部署地址：[拙政观景](http://8.147.110.194/garden/)。README 的 `cloud-home.png`、`cloud-methods.png`、`cloud-studio.png` 来自云服务器正式页面，分别展示首页、造景手法和创作功能，未展示私人账户、手机号或学生身份资料。

主视频为[正式宣传片 v2](https://github.com/UzimakeNarutoszx/personal-website-oss/releases/download/public-editions-2026-11-01/zhuozheng-promo-v2.mp4)，30 秒、1080 × 1920、有声。README 使用 `media/promo-v2-poster.jpg` 作为可点击缩略图。视频原文件不进入本仓库 Git，由 Release 提供。

这些正式展示媒体与清理源码的示意配图不同，不按 MIT 或 CC0 重新授权。摄影、设计、配音和音频等仍受各自权利约束；代码开源不授予真人肖像、学生作品、个人身份信息或第三方媒体的使用权。继续制作展示时应避免可识别真人、姓名、班级、联系方式和账户资料，不可把私人材料补回仓库。

按作者确认的范围，保留园林风景中无法辨认身份的远处游客；人像及可辨认人物照片不用于公开展示。

## 清理源码

`web/public` 的配图和动景为程序绘制的无人物示意；源码排除原实拍、学生作品、私人报告、原角色 GLB、历史账户数据与密钥。它可以用于复现应用架构与功能，但不会逐像素复现正式产品的媒体表现。

`media/home.png`、`methods.png`、`studio.png` 和 `demo.mp4` 是先前清理源码版本的 UI 截图与 9 秒无声轮播，仅保留作版本说明，不是当前主视频。应用原创代码使用根目录 MIT LICENSE，程序示意资产与第三方资产的细分边界见 [ASSETS.md](../ASSETS.md)。
