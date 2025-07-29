function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash = hash & hash;
    }
    return Math.abs(hash).toString(16);
}

export function generateSimpleAvatar(username, size = 100) {
    if (typeof username !== 'string' || username.length === 0) {
        throw new Error('Username must be a non-empty string');
    }
    const hash = simpleHash(username);
    const color = `#${hash.slice(0, 6).padStart(6, '0')}`;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // 绘制背景
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, size, size);

    // 绘制用户名首字母
    ctx.fillStyle = '#FFFFFF';
    ctx.font = `${size / 2}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(username[0].toUpperCase(), size / 2, size / 2);

    return canvas.toDataURL();
}