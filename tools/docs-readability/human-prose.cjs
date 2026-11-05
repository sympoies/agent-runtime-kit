const prose = token => (token.children || [])
  .filter(t => ['text','softbreak','hardbreak'].includes(t.type))
  .map(t => t.type === 'text' ? t.content : ' ')
  .join('').replace(/\s+/g, ' ').trim();
const label = /^\s*[-+*]\s+\*\*[^*\n]{1,80}\*\*(?:[:：]|\s)/u;
module.exports = [
  {
    names: ['HUM001','bold-label-wall'], tags: ['human-prose'],
    description: 'Rewrite three or more consecutive bold-label bullets as prose or a table',
    parser: 'markdownit', function: (params, onError) => {
      const tokens=params.parsers.markdownit.tokens;
      for (let i=0;i<tokens.length;i++) {
        const list=tokens[i]; if(list.type!=='bullet_list_open')continue;
        let run=[];
        const flush=()=>{if(run.length>=3)onError({lineNumber:run[0],detail:`${run.length} consecutive bold-label bullets`});run=[];};
        for(let j=i+1;j<tokens.length;j++){
          const t=tokens[j];
          if(t.type==='bullet_list_close'&&t.level===list.level){flush();break;}
          if(t.type==='list_item_open'&&t.level===list.level+1){
            const line=t.map[0]+1;
            if(label.test(params.lines[line-1]))run.push(line);else flush();
          }
        }
      }
    }
  },
  {
    names:['HUM002','long-prose-paragraph'],tags:['human-prose'],
    description:'Split a prose paragraph exceeding 600 visible characters',
    parser:'markdownit',function:(params,onError)=>{
      const ts=params.parsers.markdownit.tokens;
      for(let i=1;i<ts.length;i++)if(ts[i].type==='inline'&&ts[i-1].type==='paragraph_open'){
        const n=[...prose(ts[i])].length;
        if(n>600)onError({lineNumber:ts[i].map[0]+1,detail:`${n} visible characters; maximum 600`});
      }
    }
  },
  {
    names:['HUM003','presentation-clutter'],tags:['human-prose'],
    description:'Remove emoji headings and repeated em dashes in a paragraph',
    parser:'markdownit',function:(params,onError)=>{
      const ts=params.parsers.markdownit.tokens;
      for(let i=1;i<ts.length;i++)if(ts[i].type==='inline'){
        const text=prose(ts[i]),prev=ts[i-1].type;
        if(prev==='heading_open'&&/\p{Extended_Pictographic}/u.test(text))onError({lineNumber:ts[i].map[0]+1,detail:'Emoji in heading'});
        else if(prev==='paragraph_open'&&(text.match(/—/gu)||[]).length>=2)onError({lineNumber:ts[i].map[0]+1,detail:'Two or more em dashes in paragraph'});
      }
    }
  }
];
