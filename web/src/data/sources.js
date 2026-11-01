const ids = ['field-frame','field-borrow','field-opposition','field-leak','field-screen','commons-001','commons-002','commons-003']
export const sources = ids.map(id => ({ id, title: '公开版园林示意图（非实景照片）', author: '项目公开版', license: 'CC0-1.0', url: '/ASSETS.md', file: null }))
export const getSource = id => sources.find(item => item.id === id)
