var successMessagePara = $('.output-success');
var errorMessagePara = $('.output-error');

function setErrorMessage(msg) {
  errorMessagePara.text(msg);
  successMessagePara.text("");
}
function setSuccessMessage(msg) {
  successMessagePara.text(msg);
  errorMessagePara.text("");
}

$('button.local-file').on('click', function(e) {
  e.preventDefault();
  var button = $(this);
  // Button states are part of Bootstrap
  button.button('loading');
  var ajaxData = {
    'action': 'pull_local',
    'output_path': $('#local-file-path').val()
  };
  var form = $('#output-form');
  // Ajax it
  $.ajax(form.action, {
    type: 'POST',
    dataType: 'json',
    data: ajaxData,
    success: function(data) {
      if (data.success == true) {
        button.button('reset');
        window.location = data.url;
      } else {
        setErrorMessage(data.message);
        button.button('reset');
      }
    },
    error: function(response) {
      setErrorMessage("There was an un-expected error while gathering the output data.");
      button.button('reset');
    }
  });
});

$('button.remote-file').on('click', function(e) {
  e.preventDefault();
  var button = $(this);
  // Button states are part of Bootstrap
  button.button('loading');
  var ajaxData = { 'action': 'pull_remote' };
  var form = $('#output-form');
  // Ajax it
  $.ajax(form.action, {
    type: 'POST',
    dataType: 'json',
    data: ajaxData,
    success: function(data) {
      if (data.success == true) {
        button.button('reset');
        window.setTimeout(function() {
          window.location.reload();
        }, 2000);
        setSuccessMessage("Successfully downloaded remote data. Refreshing page...");
      } else {
        setErrorMessage(data.message);
        button.button('reset');
      }
    },
    error: function(response) {
      setErrorMessage("There was an un-expected error while downloading the output data.");
      button.button('reset');
    }
  });
});
