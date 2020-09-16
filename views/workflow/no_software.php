<?php
use yii\helpers\Html;

$this->title='Non-existent software';
$back_icon='<i class="fas fa-arrow-left"></i>'; 


?>

<div class="row">&nbsp;</div>

<div class="alert alert-danger" role="alert">
	<div class='row'><div class='text-center col-md-12'><h3>Error: workflow "<?=$name?> v.<?=$version?>" does not exist.</h3></div></div>
</div>

<div class="row"><div class='col-md-12 text-center'><?= Html::a("$back_icon Back to available software", ['/workflow/index'], ['class'=>'btn btn-default']) ?></div></div>