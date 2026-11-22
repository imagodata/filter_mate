// FilterMate charts: the d3 templates of the agent (show_chart), and what a chart is handed back as.
//
// Runs in a page of QtWebEngine FilterMate keeps hidden, with no network and no file (core/agent/charts.py writes the
// page, adapters/agent/chart_renderer.py loads it). A chart is drawn as SVG from a spec of data; then FMCharts.flatten
// gives it back as SVG whose look is written on each element (fill, stroke, font...), because the SVG FilterMate
// shows in the chat, writes to a file and puts in a print layout is drawn by QtSvg, which reads no style sheet, no
// "em" and no dominant-baseline.
//
// Every text of a chart is set with .text(): what a layer holds is never read as markup.
(function () {
  "use strict";

  var FONT = "'Segoe UI', 'Noto Sans', 'DejaVu Sans', Arial, sans-serif";
  var errors = [];
  window.__fmErrors = errors;
  window.addEventListener("error", function (event) {
    errors.push(String(event.message || event.error || "error") + (event.lineno ? " (line " + event.lineno + ")" : ""));
  });

  function number(value, digits) {
    if (value === null || value === undefined || !isFinite(value)) return "";
    var size = Math.abs(value);
    if (size >= 1e6 || (size > 0 && size < 1e-3)) return d3.format(".3~s")(value);
    return d3.format(digits === undefined ? ",.4~g" : digits)(value);
  }

  function svgRoot(spec) {
    var root = d3.select("#chart").append("svg")
      .attr("xmlns", "http://www.w3.org/2000/svg")
      .attr("width", spec.width).attr("height", spec.height)
      .attr("viewBox", "0 0 " + spec.width + " " + spec.height)
      .attr("font-family", FONT).attr("font-size", 11).attr("fill", spec.palette.text);
    if (spec.palette.background) {
      root.append("rect").attr("width", spec.width).attr("height", spec.height).attr("fill", spec.palette.background);
    }
    return root;
  }

  // The title, then the plot area below it: {x, y, width, height} in pixels of the SVG.
  function frame(root, spec, margins) {
    var top = 8;
    if (spec.title) {
      root.append("text").attr("x", 12).attr("y", 22).attr("font-size", 14).attr("font-weight", 600)
        .attr("fill", spec.palette.text).text(spec.title);
      top = 36;
    }
    if (spec.subtitle) {
      root.append("text").attr("x", 12).attr("y", top + 6).attr("font-size", 11)
        .attr("fill", spec.palette.muted).text(spec.subtitle);
      top += 18;
    }
    var m = Object.assign({left: 48, right: 16, bottom: 34}, margins || {});
    return {x: m.left, y: top + 8, width: Math.max(40, spec.width - m.left - m.right),
            height: Math.max(40, spec.height - top - 8 - m.bottom)};
  }

  // Recessive axes: muted text, no domain line on the value axis, a light grid.
  function styleAxis(group, palette, grid) {
    group.selectAll("text").attr("fill", palette.muted).attr("font-size", 10);
    group.selectAll("line").attr("stroke", grid ? palette.grid : palette.axis);
    group.selectAll("path.domain").attr("stroke", palette.axis);
  }

  function axisTitle(root, spec, text, x, y, rotate) {
    if (!text) return;
    var label = root.append("text").attr("font-size", 10).attr("fill", spec.palette.muted)
      .attr("text-anchor", "middle").text(text);
    label.attr("transform", "translate(" + x + "," + y + ")" + (rotate ? " rotate(-90)" : ""));
  }

  // A bar with its data end rounded (4 px), its base square on the axis.
  function barPath(x, y, width, height, horizontal) {
    var r = Math.max(0, Math.min(4, width / 2, height / 2));
    if (horizontal) {  // grows to the right from x
      return "M" + x + "," + y + "h" + (width - r) + "a" + r + "," + r + " 0 0 1 " + r + "," + r +
        "v" + (height - 2 * r) + "a" + r + "," + r + " 0 0 1 " + (-r) + "," + r + "h" + (r - width) + "Z";
    }
    return "M" + x + "," + (y + height) + "v" + (r - height) + "a" + r + "," + r + " 0 0 1 " + r + "," + (-r) +
      "h" + (width - 2 * r) + "a" + r + "," + r + " 0 0 1 " + r + "," + r + "v" + (height - r) + "Z";
  }

  function short(text, size) {
    text = String(text);
    return text.length > size ? text.slice(0, size - 1) + "…" : text;
  }

  // bar: [{label, value, others}]; one hue, the bar of the others in grey, the values written at the ends.
  function bar(spec) {
    var data = spec.data, palette = spec.palette, root = svgRoot(spec);
    var longest = d3.max(data, function (d) { return String(d.label).length; }) || 0;
    var horizontal = spec.horizontal === true || (spec.horizontal !== false && (longest > 10 || data.length > 12));
    // 0 always inside the axis: the bars grow from it, all of them negative too.
    var max = Math.max(0, d3.max(data, function (d) { return d.value; }) || 0);
    var min = Math.min(0, d3.min(data, function (d) { return d.value; }) || 0);
    var labels = data.length <= 16;
    if (horizontal) {
      var left = Math.min(spec.width * 0.4, 12 + 6 * Math.min(longest, 28));
      var f = frame(root, spec, {left: left, right: labels ? 48 : 16, bottom: spec.y_label ? 34 : 22});
      var y = d3.scaleBand().domain(d3.range(data.length)).range([f.y, f.y + f.height]).paddingInner(0.18);
      var x = d3.scaleLinear().domain([min, max]).nice().range([f.x, f.x + f.width]);
      var gx = root.append("g").attr("transform", "translate(0," + (f.y + f.height) + ")")
        .call(d3.axisBottom(x).ticks(Math.max(2, Math.floor(f.width / 80))).tickSize(-f.height).tickFormat(function (v) { return number(v); }));
      gx.select("path.domain").remove();
      styleAxis(gx, palette, true);
      var gy = root.append("g").attr("transform", "translate(" + f.x + ",0)")
        .call(d3.axisLeft(y).tickSize(0).tickPadding(6).tickFormat(function (i) { return short(data[i].label, 28); }));
      styleAxis(gy, palette, false);
      gy.selectAll("text").attr("fill", palette.text);
      root.append("g").selectAll("path").data(data).join("path")
        .attr("d", function (d, i) {
          var x0 = x(Math.min(0, d.value)), w = Math.abs(x(d.value) - x(0));
          return barPath(x0, y(i), Math.max(w, 0.5), y.bandwidth(), true);
        })
        .attr("fill", function (d) { return d.others ? palette.other : palette.series[0]; });
      if (labels) {
        root.append("g").selectAll("text").data(data).join("text")
          .attr("x", function (d) { return x(Math.max(0, d.value)) + 4; })
          .attr("y", function (d, i) { return y(i) + y.bandwidth() / 2 + 4; })
          .attr("font-size", 10).attr("fill", palette.text).text(function (d) { return number(d.value); });
      }
      axisTitle(root, spec, spec.y_label, f.x + f.width / 2, spec.height - 6, false);
    } else {
      var f2 = frame(root, spec, {left: 52, bottom: spec.x_label ? 46 : 34});
      var xb = d3.scaleBand().domain(d3.range(data.length)).range([f2.x, f2.x + f2.width]).paddingInner(0.18).paddingOuter(0.1);
      var yb = d3.scaleLinear().domain([min, max]).nice().range([f2.y + f2.height, f2.y]);
      var gy2 = root.append("g").attr("transform", "translate(" + f2.x + ",0)")
        .call(d3.axisLeft(yb).ticks(Math.max(2, Math.floor(f2.height / 50))).tickSize(-f2.width).tickFormat(function (v) { return number(v); }));
      gy2.select("path.domain").remove();
      styleAxis(gy2, palette, true);
      var size = Math.max(3, Math.floor(xb.bandwidth() / 6.5));
      var gx2 = root.append("g").attr("transform", "translate(0," + yb(0) + ")")
        .call(d3.axisBottom(xb).tickSize(0).tickPadding(6).tickFormat(function (i) { return short(data[i].label, size); }));
      styleAxis(gx2, palette, false);
      gx2.selectAll("text").attr("fill", palette.text);
      root.append("g").selectAll("path").data(data).join("path")
        .attr("d", function (d, i) {
          var top = yb(Math.max(0, d.value)), h = Math.abs(yb(d.value) - yb(0));
          return barPath(xb(i), top, xb.bandwidth(), Math.max(h, 0.5), false);
        })
        .attr("fill", function (d) { return d.others ? palette.other : palette.series[0]; });
      if (labels) {
        root.append("g").selectAll("text").data(data).join("text")
          .attr("x", function (d, i) { return xb(i) + xb.bandwidth() / 2; })
          .attr("y", function (d) { return yb(Math.max(0, d.value)) - 4; })
          .attr("text-anchor", "middle").attr("font-size", 10).attr("fill", palette.text)
          .text(function (d) { return number(d.value); });
      }
      axisTitle(root, spec, spec.x_label, f2.x + f2.width / 2, spec.height - 8, false);
      axisTitle(root, spec, spec.y_label, 12, f2.y + f2.height / 2, true);
    }
    return root;
  }

  // histogram: [{low, high, count}]; adjacent bars a gap of 2 px apart.
  function histogram(spec) {
    var data = spec.data, palette = spec.palette, root = svgRoot(spec);
    var f = frame(root, spec, {left: 52, bottom: spec.x_label ? 46 : 34});
    var low = d3.min(data, function (d) { return d.low; }), high = d3.max(data, function (d) { return d.high; });
    if (low === high) { low -= 0.5; high += 0.5; }
    var x = d3.scaleLinear().domain([low, high]).range([f.x, f.x + f.width]);
    var y = d3.scaleLinear().domain([0, d3.max(data, function (d) { return d.count; }) || 1]).nice().range([f.y + f.height, f.y]);
    var gy = root.append("g").attr("transform", "translate(" + f.x + ",0)")
      .call(d3.axisLeft(y).ticks(Math.max(2, Math.floor(f.height / 50))).tickSize(-f.width).tickFormat(function (v) { return number(v); }));
    gy.select("path.domain").remove();
    styleAxis(gy, palette, true);
    var gx = root.append("g").attr("transform", "translate(0," + (f.y + f.height) + ")")
      .call(d3.axisBottom(x).ticks(Math.max(2, Math.floor(f.width / 80))).tickFormat(function (v) { return number(v); }));
    styleAxis(gx, palette, false);
    root.append("g").selectAll("path").data(data).join("path")
      .attr("d", function (d) {
        var x0 = data.length === 1 ? f.x : x(d.low) + 1, x1 = data.length === 1 ? f.x + f.width : x(d.high) - 1;
        var h = y(0) - y(d.count);
        return d.count > 0 ? barPath(x0, y(d.count), Math.max(x1 - x0, 0.5), Math.max(h, 0.5), false) : "";
      })
      .attr("fill", palette.series[0]);
    axisTitle(root, spec, spec.x_label, f.x + f.width / 2, spec.height - 8, false);
    axisTitle(root, spec, spec.y_label || spec.count_label, 12, f.y + f.height / 2, true);
    return root;
  }

  // pie: [{label, value, others}]; a ring (donut) by default, the slices 2 px apart, a legend at the right.
  function pie(spec) {
    var data = spec.data.filter(function (d) { return d.value > 0; }), palette = spec.palette, root = svgRoot(spec);
    var f = frame(root, spec, {left: 12, right: 12, bottom: 12});
    var legendWidth = Math.min(220, f.width * 0.45);
    var radius = Math.max(20, Math.min((f.width - legendWidth) / 2, f.height / 2) - 4);
    var cx = f.x + radius + 4, cy = f.y + f.height / 2;
    var total = d3.sum(data, function (d) { return d.value; }) || 1;
    var arcs = d3.pie().sort(null).value(function (d) { return d.value; }).padAngle(2 / radius)(data);
    var arc = d3.arc().innerRadius(spec.donut === false ? 0 : radius * 0.58).outerRadius(radius).cornerRadius(2);
    var color = function (d, i) { return d.others ? palette.other : palette.series[i % palette.series.length]; };
    root.append("g").attr("transform", "translate(" + cx + "," + cy + ")").selectAll("path").data(arcs).join("path")
      .attr("d", arc).attr("fill", function (a, i) { return color(a.data, i); });
    if (spec.donut !== false) {
      root.append("text").attr("x", cx).attr("y", cy + 6).attr("text-anchor", "middle").attr("font-size", 16)
        .attr("font-weight", 600).attr("fill", palette.text).text(number(total));
    }
    var lx = cx + radius + 18, row = Math.min(20, f.height / Math.max(1, data.length));
    var ly = cy - (row * data.length) / 2 + row / 2;
    var legend = root.append("g").selectAll("g").data(data).join("g")
      .attr("transform", function (d, i) { return "translate(" + lx + "," + (ly + i * row) + ")"; });
    legend.append("rect").attr("x", 0).attr("y", -5).attr("width", 10).attr("height", 10).attr("rx", 2)
      .attr("fill", function (d, i) { return color(d, i); });
    // The label cut so that it and its share (" 100 %") end before the right edge.
    var chars = Math.max(6, Math.floor((spec.width - lx - 16 - 12) / 6.4) - 8);
    legend.append("text").attr("x", 16).attr("y", 4).attr("font-size", 11).attr("fill", palette.text)
      .text(function (d) { return short(d.label, chars) + "  " + number(100 * d.value / total, ".2~f") + " %"; });
    return root;
  }

  // line: [{x, y, series}], x a number or a date (ISO text when x_type is "time"); one line per series, 2 px.
  function line(spec) {
    var palette = spec.palette, root = svgRoot(spec), time = spec.x_type === "time";
    // A date and time without a zone is read as UTC, as the axis shows it (a local reading shifted every point).
    var utc = function (text) { return new Date(/T\d\d:\d\d(:\d\d(\.\d+)?)?$/.test(text) ? text + "Z" : text); };
    var data = spec.data.map(function (d) { return {x: time ? utc(d.x) : d.x, y: d.y, series: d.series || ""}; })
      .filter(function (d) { return d.x !== null && !(time && isNaN(d.x)) && d.y !== null && isFinite(d.y); });
    var groups = d3.groups(data, function (d) { return d.series; });
    var several = groups.length > 1;
    var f = frame(root, spec, {left: 52, right: several ? 110 : 20, bottom: spec.x_label ? 46 : 34});
    var x = (time ? d3.scaleUtc() : d3.scaleLinear()).domain(d3.extent(data, function (d) { return d.x; })).range([f.x, f.x + f.width]);
    var lo = d3.min(data, function (d) { return d.y; }), hi = d3.max(data, function (d) { return d.y; });
    var y = d3.scaleLinear().domain([Math.min(0, lo), hi]).nice().range([f.y + f.height, f.y]);
    var gy = root.append("g").attr("transform", "translate(" + f.x + ",0)")
      .call(d3.axisLeft(y).ticks(Math.max(2, Math.floor(f.height / 50))).tickSize(-f.width).tickFormat(function (v) { return number(v); }));
    gy.select("path.domain").remove();
    styleAxis(gy, palette, true);
    var axis = d3.axisBottom(x).ticks(Math.max(2, Math.floor(f.width / 90)));
    if (!time) axis.tickFormat(function (v) { return number(v); });
    var gx = root.append("g").attr("transform", "translate(0," + (f.y + f.height) + ")").call(axis);
    styleAxis(gx, palette, false);
    var path = d3.line().x(function (d) { return x(d.x); }).y(function (d) { return y(d.y); });
    groups.forEach(function (group, i) {
      var points = group[1].slice().sort(function (a, b) { return a.x - b.x; });
      var color = palette.series[i % palette.series.length];
      root.append("path").attr("d", path(points)).attr("fill", "none").attr("stroke", color)
        .attr("stroke-width", 2).attr("stroke-linejoin", "round").attr("stroke-linecap", "round");
      if (points.length <= 40) {
        root.append("g").selectAll("circle").data(points).join("circle")
          .attr("cx", function (d) { return x(d.x); }).attr("cy", function (d) { return y(d.y); }).attr("r", 3)
          .attr("fill", color).attr("stroke", palette.background || "#ffffff").attr("stroke-width", 1.5);
      }
      if (several) {  // the name at the end of its line: identity is never the colour alone
        var last = points[points.length - 1];
        root.append("text").attr("x", f.x + f.width + 6).attr("y", y(last.y) + 4).attr("font-size", 10)
          .attr("fill", palette.text).text(short(group[0], 16));
      }
    });
    axisTitle(root, spec, spec.x_label, f.x + f.width / 2, spec.height - 8, false);
    axisTitle(root, spec, spec.y_label, 12, f.y + f.height / 2, true);
    return root;
  }

  // scatter: [{x, y, series}]; dots of 4 px with a ring of the surface, three series at most (then "others").
  function scatter(spec) {
    var palette = spec.palette, root = svgRoot(spec);
    var data = spec.data.filter(function (d) { return isFinite(d.x) && isFinite(d.y); });
    var names = Array.from(new Set(data.map(function (d) { return d.series || ""; })));
    var several = names.length > 1;
    var f = frame(root, spec, {left: 52, right: several ? 110 : 20, bottom: spec.x_label ? 46 : 34});
    var x = d3.scaleLinear().domain(d3.extent(data, function (d) { return d.x; })).nice().range([f.x, f.x + f.width]);
    var y = d3.scaleLinear().domain(d3.extent(data, function (d) { return d.y; })).nice().range([f.y + f.height, f.y]);
    var gy = root.append("g").attr("transform", "translate(" + f.x + ",0)")
      .call(d3.axisLeft(y).ticks(Math.max(2, Math.floor(f.height / 50))).tickSize(-f.width).tickFormat(function (v) { return number(v); }));
    gy.select("path.domain").remove();
    styleAxis(gy, palette, true);
    var gx = root.append("g").attr("transform", "translate(0," + (f.y + f.height) + ")")
      .call(d3.axisBottom(x).ticks(Math.max(2, Math.floor(f.width / 80))).tickFormat(function (v) { return number(v); }));
    styleAxis(gx, palette, false);
    var color = function (name) {
      var i = names.indexOf(name);
      return name === spec.others_label ? palette.other : palette.series[i % palette.series.length];
    };
    var dense = data.length > 800;
    root.append("g").selectAll("circle").data(data).join("circle")
      .attr("cx", function (d) { return x(d.x); }).attr("cy", function (d) { return y(d.y); })
      .attr("r", dense ? 2.5 : 4).attr("fill", function (d) { return color(d.series || ""); })
      .attr("fill-opacity", dense ? 0.6 : 0.9)
      .attr("stroke", dense ? "none" : (palette.background || "#ffffff")).attr("stroke-width", dense ? 0 : 1);
    if (several) {
      var legend = root.append("g").selectAll("g").data(names).join("g")
        .attr("transform", function (d, i) { return "translate(" + (f.x + f.width + 10) + "," + (f.y + 8 + i * 18) + ")"; });
      legend.append("circle").attr("r", 4).attr("fill", color);
      legend.append("text").attr("x", 9).attr("y", 4).attr("font-size", 10).attr("fill", palette.text)
        .text(function (d) { return short(d, 15); });
    }
    axisTitle(root, spec, spec.x_label, f.x + f.width / 2, spec.height - 8, false);
    axisTitle(root, spec, spec.y_label, 12, f.y + f.height / 2, true);
    return root;
  }

  var KINDS = {bar: bar, histogram: histogram, pie: pie, line: line, scatter: scatter};

  // What QtSvg reads of a look, written on each element as an attribute.
  var LOOK = ["fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "stroke-dasharray", "stroke-linecap",
              "stroke-linejoin", "opacity", "font-family", "font-size", "font-weight", "font-style", "text-anchor",
              "visibility"];
  var INHERITED = {"fill": 1, "fill-opacity": 1, "stroke": 1, "stroke-width": 1, "stroke-opacity": 1,
                   "stroke-dasharray": 1, "stroke-linecap": 1, "stroke-linejoin": 1, "font-family": 1,
                   "font-size": 1, "font-weight": 1, "font-style": 1, "text-anchor": 1, "visibility": 1};

  function emToPixels(value, fontSize) {
    var text = String(value || "").trim();
    if (!text) return 0;
    if (/em$/.test(text)) return parseFloat(text) * fontSize;
    return parseFloat(text) || 0;
  }

  // The SVG of the page as text, its look written on each element; null when there is none.
  function flatten() {
    var svg = document.querySelector("#chart svg") || document.querySelector("svg");
    if (!svg) return null;
    var source = [svg].concat(Array.prototype.slice.call(svg.querySelectorAll("*")));
    var clone = svg.cloneNode(true);
    var target = [clone].concat(Array.prototype.slice.call(clone.querySelectorAll("*")));
    source.forEach(function (element, index) {
      var copy = target[index], style = getComputedStyle(element), parent = element.parentElement;
      var parentStyle = parent && element !== svg ? getComputedStyle(parent) : null;
      LOOK.forEach(function (name) {
        var value = style.getPropertyValue(name);
        if (!value) return;
        // Written once where it starts: what an element inherits as it is stays on its parent.
        if (parentStyle && INHERITED[name] && parentStyle.getPropertyValue(name) === value) return;
        copy.setAttribute(name, value);
      });
      copy.removeAttribute("style");
      copy.removeAttribute("class");
      var tag = element.tagName.toLowerCase();
      if (tag === "text") {
        var fontSize = parseFloat(style.getPropertyValue("font-size")) || 11;
        var shift = emToPixels(element.getAttribute("dy"), fontSize);
        var baseline = style.getPropertyValue("dominant-baseline");
        if (baseline === "middle" || baseline === "central") shift += 0.35 * fontSize;
        else if (baseline === "hanging" || baseline === "text-before-edge") shift += 0.8 * fontSize;
        var dx = emToPixels(element.getAttribute("dx"), fontSize);
        if (shift) copy.setAttribute("y", String((parseFloat(element.getAttribute("y")) || 0) + shift));
        if (dx) copy.setAttribute("x", String((parseFloat(element.getAttribute("x")) || 0) + dx));
        copy.removeAttribute("dy");
        copy.removeAttribute("dx");
        copy.removeAttribute("dominant-baseline");
      }
    });
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    var box = svg.getBoundingClientRect();
    if (!clone.getAttribute("width")) clone.setAttribute("width", String(Math.round(box.width) || 640));
    if (!clone.getAttribute("height")) clone.setAttribute("height", String(Math.round(box.height) || 400));
    if (!clone.getAttribute("viewBox")) {
      clone.setAttribute("viewBox", "0 0 " + clone.getAttribute("width") + " " + clone.getAttribute("height"));
    }
    return new XMLSerializer().serializeToString(clone);
  }

  // What the renderer reads: the SVG, the errors of the page, what the page holds that QtSvg does not draw.
  function result() {
    var svg = document.querySelector("#chart svg") || document.querySelector("svg");
    var unsupported = [];
    if (document.querySelector("canvas")) unsupported.push("canvas");
    if (svg && svg.querySelector("foreignObject")) unsupported.push("foreignObject");
    if (svg && svg.querySelector("image")) unsupported.push("image");
    return JSON.stringify({svg: flatten(), errors: errors.slice(0, 5), unsupported: unsupported});
  }

  window.FMCharts = {
    draw: function (spec) {
      try {
        var kind = KINDS[spec.kind];
        if (!kind) throw new Error("no template for " + spec.kind);
        kind(spec);
      } catch (error) {
        errors.push(String(error && error.message || error));
      }
    },
    // Code of the model (expert mode): the body of a function of (d3, svg, data, width, height, palette), svg an
    // empty d3 selection of the SVG to draw in.
    prepare: function (spec) {
      return svgRoot(spec);
    },
    flatten: flatten,
    result: result,
    number: number
  };
})();
