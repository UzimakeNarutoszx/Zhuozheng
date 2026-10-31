export const methods = [
  { id: 'frame', name: '框景', pinyin: 'FRAMING', summary: '把风景收进一个有边界的画面。', detail: '借助门洞、窗洞、廊柱或树枝，把视线中的景物裁出边界。框景让自然景色拥有了画幅，也让观者知道应该看哪里。', observe: '站在窗、门或廊口前，慢慢移动一步，观察画面里的主体如何变化。', image: '/assets/garden/garden-002.jpg', point: '窗洞把水面、植物和建筑裁成一幅移动的画。' },
  { id: 'borrow', name: '借景', pinyin: 'BORROWING', summary: '把园外的远处风景请进园内。', detail: '借景不是简单地看到远处，而是在特定的位置、方向和高度，让园外景物成为园中画面的一部分。', observe: '找一个视线开阔的停留点，看看墙外的塔影、树冠、天空或声音怎样延伸了空间。', image: '/assets/garden/garden-001.jpg', point: '园墙不是终点，远处的景物可以继续扩展视线。' },
  { id: 'opposition', name: '对景', pinyin: 'DIALOGUE', summary: '让两个景物隔着空间彼此回应。', detail: '在游线或水面两端安排相互呼应的景物，观者在行走和停留之间，会感到空间有了方向和节奏。', observe: '站在水岸或路径转折处，寻找视线尽头的亭、桥、石或树。', image: '/assets/garden/garden-003.jpg', point: '近景与远景相互回答，走动让画面产生节奏。' },
  { id: 'leak', name: '漏景', pinyin: 'PEEKING', summary: '让景色若隐若现地穿过花墙与漏窗。', detail: '漏窗、花墙和疏朗植物只透露景物的一部分，保留遮挡，也保留想象。看不全的景，往往更愿意让人靠近。', observe: '不要急着找完整画面，注意墙上的开口和其中露出的色块、线条与光。', image: '/assets/garden/garden-002.jpg', point: '漏窗把完整的风景拆成一组组线索。' },
  { id: 'screen', name: '障景', pinyin: 'REVEALING', summary: '先藏住，再让重要的景色出现。', detail: '用墙、石、植物或转折挡住入口的第一眼，让游线先收紧，再在下一处打开。景色的出现因此更有层次。', observe: '留意入口处的遮挡物，绕过它之后，空间怎样从窄变宽。', image: '/assets/garden/garden-003.jpg', point: '先藏后露，利用期待让空间变得更深。' }
]
export const getMethod = id => methods.find(item => item.id === id) || methods[0]
