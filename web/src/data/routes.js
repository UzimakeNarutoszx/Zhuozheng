// 园内路线：复用 data/garden-points.js 的点位，每条路线给出按步行顺序排列的站点。
// pointId 必须存在于 gardenPoints；note 用一句话说明这一站看到的是哪种造景手法。
export const gardenRoutes = [
  {
    id: 'hour',
    title: '1 小时精华',
    subtitle: '一条最短的观看线：沿水岸走一圈，让五种手法各出现一次。',
    duration: '约 60 分钟 · 5 站',
    stops: [
      {
        pointId: 'water',
        name: '水面',
        note: '先在水岸站定，越过屋檐找北寺塔：借景把墙外的远塔收进园内，视线一直延伸到园外。'
      },
      {
        pointId: 'bridge',
        name: '廊桥',
        note: '上桥时刻意不看对岸，转折与桥身先挡住一半水景，障景让绕过桥头的那一眼更有分量。'
      },
      {
        pointId: 'plant',
        name: '植物',
        note: '贴着花墙看疏枝，枝叶只漏出半池水光，漏景把完整的水面拆成若隐若现的线索。'
      },
      {
        pointId: 'hall',
        name: '远香堂',
        note: '面水而坐，望向对岸亭阁，此岸与彼岸隔水回应，对景让水面有了另一端。'
      },
      {
        pointId: 'window',
        name: '窗洞',
        note: '离开前退到窗后，让六边形窗把竹叶裁成一幅小画：框景收住脚步，也收住这一小时。'
      }
    ]
  },
  {
    id: 'half-day',
    title: '半日深度',
    subtitle: '绕水一周再回到起点，把每种手法正着看一遍、反过来再看一遍。',
    duration: '约 4 小时 · 7 站',
    stops: [
      {
        pointId: 'hall',
        name: '远香堂 · 起点',
        note: '从远香堂开始，先把对岸亭阁当作终点：对景先给视线一个落点，再决定走法。'
      },
      {
        pointId: 'window',
        name: '窗洞',
        note: '穿廊时停在窗洞前，框景告诉你该站哪里：退一步，竹叶才刚好填满六个边。'
      },
      {
        pointId: 'water',
        name: '水面',
        note: '沿水岸慢走，借景要配合位置与高度：屋檐、树冠和塔影对齐时，远塔才成立。'
      },
      {
        pointId: 'bridge',
        name: '廊桥',
        note: '上桥时让障景先挡住一半水面，走到桥心再松开视线，先藏后露的节奏会自己出现。'
      },
      {
        pointId: 'plant',
        name: '植物',
        note: '绕到花墙一侧，漏景把池水切成几段，每走一步就换一重遮挡。'
      },
      {
        pointId: 'water',
        name: '水面 · 回望',
        note: '折返水岸，回望来路：对景的方向反过来，刚才的亭阁成了新的近景。'
      },
      {
        pointId: 'hall',
        name: '远香堂 · 离园',
        note: '回到远香堂收束半日，五种手法在同一条水路上轮流出现，次序比单看一处更重要。'
      }
    ]
  },
  {
    id: 'photo',
    title: '摄影机位',
    subtitle: '按光线排的机位：先拍框，再拍倒影，最后用暮色收尾。',
    duration: '约 2 小时 · 6 站',
    stops: [
      {
        pointId: 'window',
        name: '窗洞',
        note: '正对六边形窗，把竹叶放进框内，等风停再按快门：框景本身就是构图。'
      },
      {
        pointId: 'bridge',
        name: '廊桥',
        note: '蹲低贴在桥栏，让廊柱做前景，障景的遮挡变成照片的层次，别急着越过桥。'
      },
      {
        pointId: 'water',
        name: '水面',
        note: '沿岸找低角度，让水面占下半幅：借景的北寺塔正好落在画面上方三分之一处。'
      },
      {
        pointId: 'plant',
        name: '植物',
        note: '用花窗做画中画，漏景的格子会切碎水面，把对焦点放在窗后的柳枝上。'
      },
      {
        pointId: 'hall',
        name: '远香堂',
        note: '退到堂前台阶，用柱列框住对岸亭阁：对景的呼应线正好穿过画面中心。'
      },
      {
        pointId: 'bridge',
        name: '廊桥 · 暮色',
        note: '回到廊桥拍收尾，斜光把廊柱影子拉长：同一处机位，障景的阴影会改变画面。'
      }
    ]
  }
]

// App.vue 用这个判断 #routes，避免改动现有的 utils/navigation.js（它不认识 routes 页）。
export function isRoutesHash(hash = '') {
  return String(hash).replace(/^#/, '').trim() === 'routes'
}
