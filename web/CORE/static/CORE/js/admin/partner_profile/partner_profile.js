$(window).on('load', () => {
  const parkId = $('#park_id').val()
  $('#select_partner_car_move').select2({
    dropdownParent: $('#confirm_car_move'),
  })

  getCarList(parkId)
  getPartnerList()

  $('#deleteCarBack').click(() => {
    $('#confirm_car_delete').modal('hide')
  })

  $('#moveCarBack').click(() => {
    $('#confirm_car_move').modal('hide')
  })

  $('#paramsCarBack').click(() => {
    $('#car_params').modal('hide')
  })

  $('#addLicenseBack').click(() => {
    $('#add_license').modal('hide')
  })

  $('#deleteCarParamBack').click(() => {
    $('#deleteParam').hide()
    $('#paramsPage').show()
  })

  $('#moveCarAccept').click(() => {
    const carId = $('#carIdMove').val()
    const partner_id = $('#select_partner_car_move').val()
    $.ajax({
      url: '/admin/ajax/cars/move',
      method: 'post',
      data: { car_id: carId, partner_id: partner_id },
      success: function (data) {
        getCarList(parkId)
        $('#confirm_car_move').modal('hide')
      },
    })
  })

  $('#deleteCarAccept').click(() => {
    const carId = $('#carIdDelete').val()
    $.ajax({
      url: '/admin/ajax/car/delete',
      method: 'post',
      data: { car_id: carId },
      success: function (data) {
        getCarList(parkId)
        $('#confirm_car_delete').modal('hide')
      },
    })
  })

  $('#addLicenseAccept').click(() => {
    const amount = $('#addLicenseAmount').val()
    $.ajax({
      url: `/admin/ajax/partner/${parkId}/licenses`,
      method: 'post',
      data: { delta: amount },
      success: function () {
        location.reload()
      },
    })
  })

  $('#deleteCarParamAccept').click(() => {
    const carParam = $('#deleteCarParamIDVal').val()
    $.ajax({
      url: '/admin/ajax/car/delete_input',
      method: 'post',
      data: { input_id: carParam },
      success: function (data) {
        getParamsList($('#carIdParams').val())
        $('#deleteParam').hide()
        $('#paramsPage').show()
      },
    })
  })

  $('#paramSave').click(() => {
    $.ajax({
      url: '/admin/ajax/car/add_input',
      method: 'post',
      data: {
        car_id: $('#carIdParams').val(),
        attribute: $('#paramName').val(),
        verbose_name: $('#paramVerboseName').val(),
        type: $('#paramType').val(),
        units: $('#paramUnit').val(),
      },
      success: function (data) {
        $('#paramName').val('')
        $('#paramVerboseName').val('')
        $('#paramUnit').val('')
        getParamsList($('#carIdParams').val())
      },
    })
  })
  $('#showPrice').click(() => {
    $('#pricesDiv').slideDown()
    $('#showPrice').hide()
    $('#hidePrice').show()
  })

  $('#hidePrice').click(() => {
    $('#pricesDiv').slideUp()
    $('#hidePrice').hide()
    $('#showPrice').show()
  })
})

const drawAllParamsList = (params) => {
  $('#paramsAllBody').empty()
  $('#paramsAllBody').append(
    '<div class="text-primary" style="display: flex; justify-content: space-between;"><div>Параметр</div><div>Значение</div></div>',
  )
  for (let key in params) {
    $('#paramsAllBody').append(
      '<div style="display: flex; justify-content: space-between;"><div>' +
        key +
        '</div><div>' +
        params[key] +
        '</div></div>',
    )
  }
}

const drawParamsList = (params) => {
  $('#car_params_body').empty()
  for (let param of params) {
    let td_attribute = '<td>' + param.attribute + '</td>'
    let td_verbose_name = '<td>' + param.verbose_name + '</td>'
    let td_type = '<td>' + param.type + '</td>'
    let td_units = '<td>' + param.units + '</td>'
    let td_delete =
      '<td><span class="text-danger deleteCarParamBtn" data-attribute="' +
      param.attribute +
      '" data-id="' +
      param.id +
      '" style="cursor: pointer;">Удалить</span></td>'
    $('#car_params_body').append(
      '<tr>' + td_attribute + td_verbose_name + td_type + td_units + td_delete + '</tr>',
    )
  }

  $('.deleteCarParamBtn').click((e) => {
    $('#deleteCarParamName').text(e.target.getAttribute('data-attribute'))
    $('#deleteCarParamIDVal').val(e.target.getAttribute('data-id'))
    $('#paramsPage').hide()
    $('#deleteParam').show()
  })
}

const drawCarList = (cars) => {
  $('#car_list_body').empty()
  for (let car of cars) {
    let td_car_number = '<td>' + car.car_number + '</td>'
    let td_imei = '<td>' + car.imei + '</td>'
    let td_phone_number = '<td>' + car.phone_number + '</td>'
    let td_type = '<td>' + car.model + '</td>'
    let td_commentary = '<td>' + car.commentary + '</td>'
    let td_delete =
      '<td><span class="text-danger deleteCarBtn" data-id="' +
      car.id +
      '" data-number="' +
      car.car_number +
      '" style="cursor: pointer;">Удалить</span></td>'

    let td_move =
      '<td><span class="text-warning moveCarBtn" data-id="' +
      car.id +
      '" data-number="' +
      car.car_number +
      '" style="cursor: pointer;">Перенести</span></td>'

    let td_edit_params = '<td></td>'
    if (car.backend === 'TRACCAR') {
      td_edit_params =
        '<td><span class="text-primary paramsCarBtn" data-id="' +
        car.id +
        '" data-number="' +
        car.car_number +
        '"  style="cursor: pointer;">Ред. параметры</span></td>'
    }
    $('#car_list_body').append(
      '<tr>' +
        td_car_number +
        td_imei +
        td_phone_number +
        td_type +
        td_commentary +
        td_edit_params +
        td_move +
        td_delete +
        '</tr>',
    )
  }

  $('.deleteCarBtn').click((e) => {
    $('#deleteCarNumber').text(e.target.getAttribute('data-number'))
    $('#carIdDelete').val(e.target.getAttribute('data-id'))
    $('#confirm_car_delete').modal('show')
  })

  $('.moveCarBtn').click((e) => {
    $('#moveCarNumber').text(e.target.getAttribute('data-number'))
    $('#carIdMove').val(e.target.getAttribute('data-id'))
    $('#confirm_car_move').modal('show')
  })

  $('.paramsCarBtn').click((e) => {
    $('#paramsCarNumber').text(e.target.getAttribute('data-number'))
    $('#carIdParams').val(e.target.getAttribute('data-id'))
    $('#car_params').modal('show')

    $.ajax({
      url: '/admin/ajax/car/get_inputs?car_id=' + e.target.getAttribute('data-id'),
      method: 'get',
      success: function (data) {
        drawAllParamsList(data.inputs)
      },
    })

    getParamsList(e.target.getAttribute('data-id'))
  })
}

const getParamsList = (id) => {
  $.ajax({
    url: '/admin/ajax/car?car_id=' + id,
    method: 'get',
    success: function (data) {
      drawParamsList(data.car.inputs)
    },
  })
}

const getCarList = (parkId) => {
  $.ajax({
    url: '/admin/ajax/cars/list?partner_id=' + parkId,
    method: 'get',
    success: function (data) {
      drawCarList(data.cars)
    },
  })
}

const getPartnerList = () => {
  $.ajax({
    url: '/admin/ajax/partner/list',
    method: 'get',
    success: function (data) {
      $('#select_partner_car_move').empty()
      for (let partner of data.partners) {
        $('#select_partner_car_move').append(
          '<option value="' + partner.id + '">' + partner.name + '</option>',
        )
      }
    },
  })
}
