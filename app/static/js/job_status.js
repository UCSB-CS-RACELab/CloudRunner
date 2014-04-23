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
        alert(data.message);
        button.button('reset');
      }
    },
    error: function(response) {
      alert("There was an un-expected error while gathering the output data.");
      button.button('reset');
    }
  });
});