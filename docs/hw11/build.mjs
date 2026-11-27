import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Presentation,PresentationFile} from 'file:///C:/Users/Elitebook/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const assets=path.join(root,'assets');
const deck=Presentation.create({slideSize:{width:1920,height:1080}});
const N='#0C2038',T='#168B87',G='#536374';
function text(s,v,x,y,w,h,size=32,color=N,bold=false){
 const z=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 z.text=v;z.text.style={typeface:'Segoe UI',fontSize:size,color,bold,verticalAlignment:'middle'};return z;
}
async function image(s,file,x,y,w,h,box){
 const crop=box?{left:box[0]/1920,top:box[1]/1080,right:(1920-box[2])/1920,bottom:(1080-box[3])/1080}:undefined;
 s.images.add({blob:new Uint8Array(await fs.readFile(path.join(assets,file))),contentType:'image/png',alt:file,fit:'contain',position:{left:x,top:y,width:w,height:h},...(crop?{crop}:{})});
}
function slide(title,n){const s=deck.slides.add();s.background.fill='#FFFFFF';text(s,title,70,47,1780,86,52,N,true);text(s,'RC ATLAS',70,1022,400,30,21,G,true);text(s,`${n} / 5`,1760,1022,90,30,21,G);return s;}
const notes=[
`Hello, my name is Raimundo Antonio Cumba. I developed RC Atlas as part of Advanced Programming at Eötvös Loránd University. RC Atlas brings programme planning, operational work and management oversight into one workspace. Today I will introduce the platform briefly and then follow one task from assignment to final approval. These are authentic application screenshots, so the complete demonstration is available here without a live connection.`,
`RC Atlas covers portfolio and project management, operational planning, monitoring and indicator work, analytics and risks, reporting and narratives, and role-based governance. These areas are at different stages of development. Portfolio oversight and the task workflow are implemented. Indicator analysis depends on configured methods and suitable data, and some analytical capabilities are only partially exposed. Report previews and contextual narratives are available, while the proposed report export and delivery options remain unavailable. The screenshot shows the current accepted Programme Manager interface. Its figures come from synthetic data. In particular, the displayed zero portfolio health should not be interpreted as a verified outcome: the distinction between missing values and zero remains an open issue. We now move from this broad overview to one concrete operational workflow.`,
`Our task is Review Buzi field report, within the Coastal Resilience and Livelihoods Programme. First, Teresa Mbanze, acting as Programme Manager, defines the activity and assigns it to Aline Duarte, the Field Coordinator. The deadline is 1 December 2026. The form requires evidence and selects Validation plus Approval. Raimundo Cumba is the validator and Teresa is the final approver. This capture shows the filled creation form before Create Task. Once created, the task begins as Not Started. In the second image, Aline has accessed her assigned task and started work. The displayed status is In Progress and the recorded progress is 25 percent. The same task title, assignee and deadline connect these two views.`,
`Next, Aline prepares the submission. She enters 100 percent progress, adds the synthetic evidence note “Synthetic Buzi field report reviewed”, and writes “Ready for independent validation.” The first image shows the filled form just before she selects Submit for Validation, so its header still reflects the earlier In Progress state. After submission, the task appears as Pending Validation in the MEAL Officer's workspace, with one evidence entry and three comments. Raimundo reviews it and can either Validate or Request Rework. Validation advances the review stage to approval; it does not close the task. Finally, Teresa grants approval. The third screenshot shows the resulting Completed status, the Complete stage, the named validator and approver, and the Approved indicator. The retained history records validation followed by final approval. Execution, validation and approval belong to distinct responsibilities. The evidence in this example is a synthetic text note, not an uploaded real field report.`,
`The approved task is now visible in the Programme Manager's Workplan under the Completed filter. The row retains the task title, Aline's ownership, the deadline, 100 percent progress and the evidence count. This illustrates accountability through assigned responsibilities, traceability through documented transitions, and visibility through centralized oversight. A completed task confirms operational delivery; it does not by itself prove programme outcomes or impact. The broader platform can be explored through the promotional website shown here. This demonstration uses synthetic data and RC Atlas remains under active development. The goal is turning project plans into accountable operational delivery. Thank you.`
];
let s=deck.slides.add();s.background.fill=N;
await image(s,'rc-atlas-logo@2x.png',66,65,330,220);
text(s,'RC Atlas: From Planning\nto Accountable Delivery',82,310,1700,205,83,'#FFFFFF',true);
text(s,'An integrated operational intelligence platform for\ndevelopment and humanitarian programmes.',86,562,1500,120,39,'#DCE8EC');
text(s,'Raimundo Antonio Cumba',86,813,1200,55,37,'#FFFFFF',true);
text(s,'Eötvös Loránd University (ELTE)\nAdvanced Programming — 2026',86,883,1400,90,29,'#DCE8EC');
text(s,'1 / 5',1760,1022,90,30,21,'#DCE8EC');
s.speakerNotes.text=notes[0]+'\nSource: assets/rc-atlas-logo@2x.png (unchanged official promo/logo@2x.png).';
s=slide('One Platform, Multiple Capabilities',2);
const caps=[['Portfolio and project management','Implemented portfolio oversight'],['Operational planning and task management','Implemented assignment-to-approval workflow'],['Monitoring, evaluation and indicators','Partial exposure; methods and data required'],['Performance analytics and risk monitoring','Implemented views; analytical limitations remain'],['Reporting and contextual narratives','Previews available; export and delivery unavailable'],['Role-based governance and accountability','Implemented access and workflow responsibilities']];
caps.forEach((a,i)=>{text(s,a[0],70,177+i*123,595,62,30,N,true);text(s,a[1],70,235+i*123,595,52,23,i===2||i===4?G:T);});
await image(s,'01-portfolio-overview.png',700,180,1150,647);
text(s,'Programme Manager / Current accepted UI-01',700,848,1150,42,27,T,true);
text(s,'Synthetic values illustrate the interface, not verified performance.\nMissing-versus-zero analytical presentation remains under review.',700,905,1150,70,24,G);
s.speakerNotes.text=notes[1]+'\nSources: assets/01-portfolio-overview.png; UI-01 FEATURE_EXPOSURE.md and accepted Batch 2 records. Overview uses a separate current synthetic fixture, not the historical task session.';
s=slide('From Task Assignment to Execution',3);
text(s,'“Review Buzi field report” / Coastal Resilience and Livelihoods Programme',70,138,1780,53,31,G);
text(s,'1  Programme Manager: Assign the task',70,225,1140,57,35,T,true);
text(s,'2  Field Coordinator: Start execution',1250,225,600,90,35,T,true);
await image(s,'02-task-creation-assignment.png',70,322,1120,420,[260,180,1900,795]);
await image(s,'03-task-in-progress.png',1250,337,600,260,[465,310,1080,576]);
text(s,'Aline Duarte: assignee\nRaimundo Cumba: validator\nTeresa Mbanze: approver',70,783,590,150,31,N);
text(s,'Due 1 December 2026\nEvidence required\nValidation + Approval',680,783,540,150,31,N);
text(s,'Not Started → In Progress',1250,667,600,57,33,T,true);
text(s,'The assigned task is underway.\nRecorded progress: 25%.',1250,749,600,100,31,N);
text(s,'Creation form shown before Create Task. All named participants are demo users.',70,962,1720,39,24,G);
s.speakerNotes.text=notes[2]+'\nSources: assets/02-task-creation-assignment.png; assets/03-task-in-progress.png; HW10 authentic-demo/WORKFLOW_RECORD.md. Native crop coordinates are in build.mjs. Date input is US locale 12/01/2026.';
s=slide('Evidence, Validation and Approval',4);
text(s,'One task, three distinct responsibilities',70,140,1780,48,32,G);
const xs=[70,675,1280];
const heads=['3  Submit evidence','4  Validate','5  Approve'];
const roles=['Field Coordinator','MEAL Officer','Programme Manager'];
for(let i=0;i<3;i++){text(s,heads[i],xs[i],221,565,58,37,T,true);text(s,roles[i],xs[i],280,565,45,29,N,true);}
await image(s,'04-task-submission.png',70,350,565,510,[465,310,1080,865]);
await image(s,'05-task-validation.png',675,350,565,444,[465,292,1080,775]);
await image(s,'06-final-approval.png',1280,350,565,539,[1295,15,1905,597]);
text(s,'Evidence note + comment\nBefore Submit for Validation',70,914,565,76,27,G);
text(s,'Pending Validation\nValidate or Request Rework',675,914,565,76,27,G);
text(s,'Completed / Approved\nAfter final approval',1280,914,565,76,27,G);
s.speakerNotes.text=notes[3]+'\nSources: assets/04-task-submission.png, 05-task-validation.png, 06-final-approval.png; HW10 evidence/record4/workflow.json. Screenshots are crops, not reconstructed UI. Approval-stage task status remains pending_validation until approval closes it.';
s=slide('From Completed Work to Management Intelligence',5);
text(s,'Programme Manager / Completed Workplan',70,151,1780,50,31,T,true);
await image(s,'07-completed-workplan.png',70,233,1780,422,[260,108,1900,497]);
const benefits=[['Accountability','Clearly assigned responsibilities'],['Traceability','Documented operational transitions'],['Visibility','Centralized oversight of progress']];
benefits.forEach((b,i)=>{text(s,b[0],70+i*605,704,565,55,36,T,true);text(s,b[1],70+i*605,766,565,64,29,N);});
text(s,'“Turning project plans into accountable operational delivery.”',70,858,1780,62,38,N,true);
text(s,'https://esst-prog2.github.io/RC_ATLAS_Project/',70,942,1320,42,29,T);
text(s,'Synthetic demonstration data. Application under active development.',70,995,1610,36,23,G);
s.speakerNotes.text=notes[4]+'\nSources: assets/07-completed-workplan.png; docs/hw10/authentic-demo/publication/PUBLICATION_REPORT.md (published promotional URL). Task completion is not evidence of measured programme outcomes.';
await fs.mkdir(path.join(root,'.build'),{recursive:true});
await (await PresentationFile.exportPptx(deck)).save(path.join(root,'.build','candidate.pptx'));
await fs.writeFile(path.join(root,'SPEAKER_NOTES.md'),'# RC Atlas — speaker notes\n\nSuggested duration: approximately 5–6 minutes.\n\n'+notes.map((n,i)=>`## Slide ${i+1}\n\n${n}\n`).join('\n'));
console.log('Created five-slide candidate and speaker notes');

