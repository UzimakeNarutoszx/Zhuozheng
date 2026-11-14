// 同一处景色，换一种手法看：对照页数据。
// 说明文字是观察性整理，具体出处与论文引用见各手法详情页。

export const comparisons = [
  {
    id: 'who-sits',
    title: '与谁同坐轩',
    subtitle: '扇面亭里的一次取景',
    intro: '同一个扇面窗，换一种看法，画面里的主角就变了。',
    methods: [
      { methodId: 'frame', observe: '扇形的窗洞把水面、荷叶和远处的屋檐裁成一幅扇形画。' },
      { methodId: 'borrow', observe: '从亭内向外看，园外的树影和屋檐被借进画面，园墙不再是终点。' },
      { methodId: 'opposition', observe: '亭与对岸的景物隔水相望，视线从这一岸落到那一岸。' }
    ]
  },
  {
    id: 'far-fragrance',
    title: '远香堂',
    subtitle: '隔水看对岸的亭子',
    intro: '站在堂前，先被水面挡住，再被对岸接住。',
    methods: [
      { methodId: 'opposition', observe: '远香堂与雪香云蔚亭隔水相对，此岸与彼岸互相成为画面。' },
      { methodId: 'borrow', observe: '向北望，园外的北寺塔从树梢和屋檐之间露出来。' },
      { methodId: 'screen', observe: '近处的山石和树丛先挡住一部分视线，绕行后才展开对岸。' }
    ]
  },
  {
    id: 'pipa-court',
    title: '枇杷园',
    subtitle: '月洞门与漏窗之间',
    intro: '门洞给你一个完整的框，漏窗只给你一些线索。',
    methods: [
      { methodId: 'frame', observe: '月洞门把门后的枇杷、湖石和粉墙收成一个圆形的画面。' },
      { methodId: 'leak', observe: '漏窗只透出枝叶和水面的一小部分，走一步就换一个局部。' },
      { methodId: 'screen', observe: '院墙和花木先遮住后景，转过门洞才看见里面的院子。' }
    ]
  }
]

export const getComparison = id => comparisons.find(item => item.id === id) || comparisons[0]
