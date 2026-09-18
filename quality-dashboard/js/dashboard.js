// 质量度量看板 - ECharts 图表逻辑
// 6 个图表：通过率趋势、覆盖率趋势、用例分布饼图、流水线时长趋势、质量雷达图、指标说明

// 通用配置
const COLORS = {
    blue: '#5470c6',
    green: '#91cc75',
    yellow: '#fac858',
    red: '#ee6666',
    cyan: '#73c0de',
    orange: '#fc8452'
};

// 初始化所有图表
let charts = {};

function initCharts() {
    charts.passRate = echarts.init(document.getElementById('passRateChart'));
    charts.coverage = echarts.init(document.getElementById('coverageChart'));
    charts.caseDist = echarts.init(document.getElementById('caseDistChart'));
    charts.duration = echarts.init(document.getElementById('durationChart'));
    charts.radar = echarts.init(document.getElementById('radarChart'));
}

// 更新卡片数据
function updateCards(data) {
    const s = data.summary;
    document.getElementById('lastUpdated').textContent = s.last_updated;
    document.getElementById('passRate').textContent = s.pass_rate.toFixed(1) + '%';
    document.getElementById('coverage').textContent = s.coverage.toFixed(1) + '%';
    document.getElementById('bugs').textContent = s.bugs_online;
    document.getElementById('duration').textContent = s.regression_duration;

    // 计算趋势
    const prTrend = document.getElementById('passRateTrend');
    const prData = data.trends.pass_rate;
    if (prData.length >= 2) {
        const diff = prData[prData.length-1].value - prData[prData.length-2].value;
        prTrend.textContent = (diff >= 0 ? '+' : '') + diff.toFixed(1) + '%';
        prTrend.className = 'card-trend ' + (diff > 0 ? 'up' : diff < 0 ? 'down' : 'neutral');
    }

    const covTrend = document.getElementById('coverageTrend');
    const covData = data.trends.coverage;
    if (covData.length >= 2) {
        const diff = covData[covData.length-1].value - covData[covData.length-2].value;
        covTrend.textContent = (diff >= 0 ? '+' : '') + diff.toFixed(1) + '%';
        covTrend.className = 'card-trend ' + (diff > 0 ? 'up' : diff < 0 ? 'down' : 'neutral');
    }

    const durTrend = document.getElementById('durationTrend');
    const durData = data.trends.duration;
    if (durData.length >= 2) {
        const diff = durData[durData.length-1].value - durData[durData.length-2].value;
        durTrend.textContent = (diff <= 0 ? '快了 ' : '慢了 ') + Math.abs(diff) + 'min';
        durTrend.className = 'card-trend ' + (diff <= 0 ? 'up' : 'down');
    }

    const bugsTrend = document.getElementById('bugsTrend');
    bugsTrend.textContent = '当前 ' + s.bugs_online + ' 个';
    bugsTrend.className = 'card-trend neutral';
}

// 通过率趋势折线图
function renderPassRateChart(data) {
    const trend = data.trends.pass_rate;
    charts.passRate.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: {
            type: 'category',
            data: trend.map(d => d.date.slice(5)),
            axisLabel: { color: '#999' }
        },
        yAxis: {
            type: 'value',
            min: 80,
            max: 100,
            axisLabel: { color: '#999', formatter: '{value}%' }
        },
        series: [{
            data: trend.map(d => d.value),
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color: COLORS.blue },
            lineStyle: { width: 3 },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(84,112,198,0.3)' },
                    { offset: 1, color: 'rgba(84,112,198,0.05)' }
                ])
            },
            markLine: {
                silent: true,
                data: [{ yAxis: 95, name: '目标95%', lineStyle: { color: COLORS.green, type: 'dashed' } }]
            }
        }],
        grid: { left: '8%', right: '5%', top: '10%', bottom: '15%' }
    });
}

// 覆盖率趋势折线图
function renderCoverageChart(data) {
    const trend = data.trends.coverage;
    charts.coverage.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: {
            type: 'category',
            data: trend.map(d => d.date.slice(5)),
            axisLabel: { color: '#999' }
        },
        yAxis: {
            type: 'value',
            min: 60,
            max: 100,
            axisLabel: { color: '#999', formatter: '{value}%' }
        },
        series: [{
            data: trend.map(d => d.value),
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color: COLORS.green },
            lineStyle: { width: 3 },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(145,204,117,0.3)' },
                    { offset: 1, color: 'rgba(145,204,117,0.05)' }
                ])
            },
            markLine: {
                silent: true,
                data: [{ yAxis: 70, name: '门禁70%', lineStyle: { color: COLORS.red, type: 'dashed' } }]
            }
        }],
        grid: { left: '8%', right: '5%', top: '10%', bottom: '15%' }
    });
}

// 用例分布饼图
function renderCaseDistChart(data) {
    charts.caseDist.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: { bottom: 5, textStyle: { color: '#666' } },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '45%'],
            data: data.case_distribution,
            label: { color: '#666' },
            itemStyle: {
                borderColor: '#fff',
                borderWidth: 2
            },
            color: [COLORS.blue, COLORS.green, COLORS.yellow, COLORS.cyan]
        }]
    });
}

// 流水线时长趋势图
function renderDurationChart(data) {
    const trend = data.trends.duration;
    charts.duration.setOption({
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return params[0].name + '<br/>耗时: ' + params[0].value + ' 分钟';
            }
        },
        xAxis: {
            type: 'category',
            data: trend.map(d => d.date.slice(5)),
            axisLabel: { color: '#999' }
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#999', formatter: '{value}min' }
        },
        series: [{
            data: trend.map(d => d.value),
            type: 'bar',
            barWidth: '50%',
            itemStyle: {
                color: function(params) {
                    return params.value <= 30 ? COLORS.green : COLORS.red;
                },
                borderRadius: [4, 4, 0, 0]
            },
            markLine: {
                silent: true,
                data: [{ yAxis: 30, name: '目标30min', lineStyle: { color: COLORS.orange, type: 'dashed' } }]
            }
        }],
        grid: { left: '12%', right: '5%', top: '10%', bottom: '15%' }
    });
}

// 质量雷达图
function renderRadarChart(data) {
    const radar = data.radar;
    charts.radar.setOption({
        tooltip: {},
        radar: {
            indicator: radar.indicators,
            shape: 'polygon',
            radius: '65%',
            splitNumber: 5,
            axisName: { color: '#666', fontSize: 12 },
            splitArea: {
                areaStyle: {
                    color: ['#fafafa', '#f0f0f0', '#fafafa', '#f0f0f0', '#fafafa']
                }
            },
            splitLine: { lineStyle: { color: '#e0e0e0' } },
            axisLine: { lineStyle: { color: '#e0e0e0' } }
        },
        series: [{
            type: 'radar',
            data: [{
                value: radar.values,
                name: '当前质量',
                areaStyle: { color: 'rgba(84,112,198,0.2)' },
                lineStyle: { color: COLORS.blue, width: 2 },
                itemStyle: { color: COLORS.blue }
            }]
        }]
    });
}

// 加载数据并渲染
async function loadAndRender() {
    try {
        const resp = await fetch('data/metrics.json');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();

        updateCards(data);
        renderPassRateChart(data);
        renderCoverageChart(data);
        renderCaseDistChart(data);
        renderDurationChart(data);
        renderRadarChart(data);
    } catch(e) {
        console.error('Failed to load metrics:', e);
        document.getElementById('lastUpdated').textContent = '加载失败: ' + e.message;
    }
}

// 窗口resize
window.addEventListener('resize', function() {
    Object.values(charts).forEach(c => c && c.resize());
});

// 启动
initCharts();
loadAndRender();
