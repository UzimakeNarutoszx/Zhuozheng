# 拙政观景

独立的拙政园造景手法互动出版网站。

## 启动

日常使用：双击项目根目录的 `启动拙政观景.command`，它会启动或复用前后端并打开 `http://127.0.0.1:4173/`。详见 [项目启动说明](../README.md)。

首次安装前端依赖：

```bash
npm install
```

手动开发时可运行 `npm run dev -- --host 127.0.0.1 --port 4173 --strictPort`，并另行启动后端。不要直接双击 `index.html`；开发入口需要由 Vite 提供模块资源。

## 构建

```bash
npm run build
npm run preview
```

正式图片、来源和许可记录位于 `public/sources/`。地图使用 Leaflet 加 OpenStreetMap 在线底图，需要联网显示瓦片；地图标注与观察内容仍由本项目维护。网站不依赖项目外部目录。
