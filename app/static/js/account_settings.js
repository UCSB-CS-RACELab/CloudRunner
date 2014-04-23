$('#password').on('keydown', function(e) {
  console.log(e.keyCode);
  var newPasswordInput = $(this);
  var currentPasswordDiv = $('div.current-pass');
  
  if (newPasswordInput.val().length == 1 && e.keyCode == 8) {
    // About to delete last character
    if (!currentPasswordDiv.hasClass('hidden')) {
      currentPasswordDiv.addClass('hidden');
    }
  }
  else if (newPasswordInput.val().length == 0 && 48 <= e.keyCode && e.keyCode <= 90) {
    // About to type first character 0-9a-z
    if (currentPasswordDiv.hasClass('hidden')) {
      currentPasswordDiv.removeClass('hidden');
    }
  }
});
$('#submit-btn').on('click', function(e) {
  // Name and email validations -- just length based
  var nameInput = $('#name');
  var emailInput = $('#email');
  
  var formInputs = [$('#name'), $('#email')];
  var invalid = false;
  for (var i = 0; i < 2; i++)
  {
    var formInput = formInputs[i];
    if (formInput.val().length == 0)
    {
      // Cant change these inputs to be blank
      invalid = true;
      // Use bootstraps form control states, which need to be placed on outer div
      var enclosingDiv = formInput.closest('div.form-group');
      // Only need to add this stuff if its not already there
      if (!enclosingDiv.hasClass('has-error'))
      {
        var errorMessageHTML = '<span class="glyphicon glyphicon-remove form-control-feedback"></span>'
        errorMessageHTML += '\n<span class="help-inline text-danger">This field can&#39;t be blank.</span>';
        enclosingDiv.addClass('has-error').addClass('has-feedback');
        formInput.after(errorMessageHTML);
      }
    }
    else
    {
      // Need to make sure we remove any errors that we might have placed on it
      var enclosingDiv = formInput.closest('div.form-group');
      if (enclosingDiv.hasClass('has-error'))
      {
        enclosingDiv.removeClass('has-error').removeClass('has-feedback');
        // Here we use the fact that the span.help-inline and span.glyphicon elements
        // will be placed as the next sibling in the DOM
        formInput.next().remove();
        formInput.next().remove();
      }
    }
  }
  if (invalid) {
    // Dont send the POST or check other fields
    e.preventDefault();
    return;
  }
  // Name and email should be good now
  // Password validations
  var password = $('#password');
  var passwordConfirmation = $('#password_conf');
  // First need to make sure new password matches confirmation
  if (password.val() == passwordConfirmation.val()) {
    if (password.closest('div.form-group').hasClass('has-error')) {
      password.closest('div.form-group').removeClass('has-error').removeClass('has-feedback');
      passwordConfirmation.closest('div.form-group').removeClass('has-error').removeClass('has-feedback');
      password.next().remove();
      passwordConfirmation.next().remove();
    }
  } else {
    // Password mismatch, need to re-enter
    e.preventDefault();
    // Use bootstraps form control states, which need to be placed on outer div
    var errorMessageHTML = '<span class="glyphicon glyphicon-remove form-control-feedback"></span>'
    errorMessageHTML += '\n<span class="help-inline text-danger">Password and password confirmation do not match.</span>';
    if (!password.closest('div.form-group').hasClass('has-error')) {
      password.closest('div.form-group').addClass('has-error').addClass('has-feedback');
      passwordConfirmation.closest('div.form-group').addClass('has-error').addClass('has-feedback');
      password.after(errorMessageHTML);
      passwordConfirmation.after(errorMessageHTML);
    }
  }
  // If a new password was actually entered, we also need to check for a current password
  var currentPassword = $('#password_curr');
  if (password.val().length > 0 && currentPassword.val().length == 0) {
    // Might be redundant if passwords didnt match, but no harm done
    e.preventDefault();
    if (!currentPassword.closest('div.form-group').hasClass('has-error')) {
      var errorMessageHTML = '<span class="glyphicon glyphicon-remove form-control-feedback"></span>'
      errorMessageHTML += '\n<span class="help-inline text-danger">You need to provide your current password in order to change it.</span>';
      currentPassword.closest('div.form-group').addClass('has-error').addClass('has-feedback');
      currentPassword.after(errorMessageHTML);
    }
  }
});