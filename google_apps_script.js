function doGet(e) {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = sheet.getDataRange().getValues();
    var headers = data.shift();
    var json = data.map(function (row) {
        var obj = {};
        headers.forEach(function (header, i) {
            obj[header] = row[i];
        });
        return obj;
    });
    return ContentService.createTextOutput(JSON.stringify(json)).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
    var requestData = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    if (requestData.action === 'add') {
        sheet.appendRow([
            requestData.User,
            requestData.GPU_ID,
            requestData.GPU_Type,
            requestData.Start,
            requestData.End,
            requestData.Project
        ]);
    } else if (requestData.action === 'delete') {
        var rowsToDelete = requestData.rows;
        // Sort descending to delete from bottom to top so indices don't shift
        rowsToDelete.sort(function (a, b) { return b - a; });
        rowsToDelete.forEach(function (row) {
            sheet.deleteRow(row);
        });
    }

    return ContentService.createTextOutput("Success").setMimeType(ContentService.MimeType.TEXT);
}
