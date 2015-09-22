function setActDate() {
    var today = new Date();
    var dd = today.getDate();
    var mm = today.getMonth() + 1;
    //January is 0!
    var yyyy = today.getFullYear();
    
    if (dd < 10) {
        dd = '0' + dd
    }
    
    if (mm < 10) {
        mm = '0' + mm
    }
    
    today = yyyy + '-' + mm + '-' + dd + '%';
    
    jQuery("#getsms input[name=date]").val(today)
}

$.tablesorter.addParser({
    id: "customDate",
    is: function(s) {
        //return false;
        //use the above line if you don't want table
        //sorter to auto detected this parser
        //else use the below line.
        //attention: doesn't check for invalid stuff
        //2009-77-77 77:77:77.0 would also be matched
        //if that doesn't suit you alter the regex to
        //be more restrictive
        return /\d{1,4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}\.\d+/.test(s);
    },
    format: function(s) {
        s = s.replace(/\-/g, " ");
        s = s.replace(/:/g, " ");
        s = s.replace(/\./g, " ");
        s = s.split(" ");
        return jQuery.tablesorter.formatFloat(((new Date(s[0],s[1] - 1,s[2],s[3],s[4],s[5]).getTime()) * 1000) + parseInt(s[6]));
    },
    type: "numeric"
});

window.onload = function() {
    getRouting();
}
;
function getAllSms() {
    var datum = jQuery("#getsms input[name=date]").val();
    jQuery('div.sms').load('ajax/getsms', {
        all: "true",
        date: datum
    }, function() {
        if (jQuery("#sessiontimeout").length) {
            location.reload();
        }
        jQuery("#smsTable").tablesorter(
        {
            headers: {
                5: {
                    sorter: 'customDate'
                },
                8: {
                    sorter: 'customDate'
                }
            },
            sortList: [[5, 1], [8, 1]],
            theme: 'blue',
            widgets: ["zebra", "filter"],
            widthFixed: true
        });
    }
    );
}
function getSms() {
    var datum = jQuery("#getsms input[name=date]").val();
    jQuery('div.sms').load('ajax/getsms', {
        all: "false",
        date: datum
    }, function() {
        if (jQuery("#sessiontimeout").length) {
            location.reload();
        }
        jQuery("#smsTable").tablesorter(
        {
            headers: {
                5: {
                    sorter: 'customDate'
                },
                8: {
                    sorter: 'customDate'
                }
            },
            sortList: [[5, 1], [8, 1]],
            theme: 'blue',
            widgets: ["zebra", "filter"],
            widthFixed: true
        });
    }
    );
}

function getStatus() {
    
    jQuery.post("ajax/status", function(data) {
        if (jQuery("#sessiontimeout").length) {
            location.reload();
        }
        
        var status = JSON.parse(data);
        
        jQuery("#routerstatus").html(status['router']);
        if (status['router'] == 'alive') {
            jQuery("#routerstatus").css("background", "#669933");
        } else {
            JQuery("#routerstatus").css("background", "#E24C34");
        }
        jQuery("#watchdogstatus").html(status['watchdog']);
        if (status['watchdog'] == 'alive') {
            jQuery("#watchdogstatus").css("background", "#669933");
        } else {
            jQuery("#watchdogstatus").css("background", "#E24C34");
        }
    }
    );
}


function getRouting() {
    jQuery('div.routing').load('ajax/getrouting', function() {
        if (jQuery("#sessiontimeout").length) {
            location.reload();
        }
        jQuery("#routingTable").tablesorter(
        {
            headers: {
                0: {
                    sorter: 'customDate'
                }
            },
            sortList: [[0, 1], [9, 1]],
            theme: 'blue'
        });
    }
    );
    getStatus();
}
$(document).ready(function() {
    setActDate();
    
    jQuery("#getsms").submit(function(event) {
        // Stop form from submitting normally
        event.preventDefault();
        
        // Get some values from elements on the page:
        var $form = $(this)
          , 
        dat = $form.find("input[name='date']").val()
          , 
        mob = $form.find("input[name='mobile']").val()
          , 
        url = $form.attr("action");
        
        // Send the data using post
        var posting = $.post(url, {
            date: dat,
            mobile: mob
        });
        
        // Put the results in a div
        posting.done(function(data) {
            jQuery("div.sms").empty().append(data);
            jQuery("#smsTable").tablesorter(
            {
                headers: {
                    5: {
                        sorter: 'customDate'
                    },
                    8: {
                        sorter: 'customDate'
                    }
                },
                sortList: [[5, 1], [8, 1]],
                theme: 'blue',
                widgets: ["zebra", "filter"]
            });
        }
        );
    }
    );
}
);
