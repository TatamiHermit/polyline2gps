var marker

var map = new AMap.Map("container", {
    resizeEnable: true,
//    center: [116.397428, 39.90923],
    center:lineArr[0],
    zoom: 17
});

marker = new AMap.Marker({
    map: map,
//    position: [116.478935,39.997761],
    position: lineArr[0],
    icon: "https://webapi.amap.com/images/car.png",
    offset: new AMap.Pixel(-26, -13),
    autoRotation: true,
    angle:-90,
});


var polyline = new AMap.Polyline({
    map: map,
    path: lineArr,
    showDir:true,
    strokeColor: "#28F",
    strokeOpacity: 1,
    strokeWeight: 6,
});

var passedPolyline = new AMap.Polyline({
    map: map,
    strokeColor: "#AF5",
    strokeWeight: 6,
});


marker.on('moving', function (e) {
    passedPolyline.setPath(e.passedPath);
});

map.setFitView();

//function startAnimation () {
//    marker.moveAlong(lineArr, 8000);
//}

function pauseAnimation () {
    marker.pauseMove();
}

function resumeAnimation () {
    marker.resumeMove();
}

function stopAnimation () {
    marker.stopMove();
}