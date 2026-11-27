svg.selectAll('*').remove();
svg.append('rect').attr('width',width).attr('height',height).attr('fill','#ffffff');
const m={left:65,right:20,top:15,bottom:55};
const x=d3.scaleLinear().domain([d3.min(data,d=>d.low),d3.max(data,d=>d.high)]).range([m.left,width-m.right]);
const y=d3.scaleLinear().domain([0,d3.max(data,d=>d.count)]).nice().range([height-m.bottom,m.top]);
svg.append('g').attr('transform',`translate(0,${height-m.bottom})`).call(d3.axisBottom(x).ticks(5).tickFormat(d=>d+' %'));
svg.append('g').attr('transform',`translate(${m.left},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('d'))).call(g=>g.select('.domain').remove());
svg.selectAll('rect.bin').data(data).join('rect').attr('class','bin').attr('x',d=>x(d.low)+1).attr('y',d=>y(d.count)).attr('width',d=>Math.max(1,x(d.high)-x(d.low)-2)).attr('height',d=>y(0)-y(d.count)).attr('fill','#168cad').attr('rx',2);
svg.selectAll('.tick text').attr('font-size',21).attr('fill','#54717e');
